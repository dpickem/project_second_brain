#!/usr/bin/env python3
"""
Run All Tests - Unified Test Runner for Second Brain

This script runs all tests across the project:
- Backend unit tests (Python/pytest)
- Backend integration tests (Python/pytest)
- Frontend unit tests (JavaScript/Vitest)
- Frontend e2e tests (JavaScript/Playwright)

Usage:
    python scripts/run_all_tests.py              # Run all tests (backend + frontend unit/e2e)
    python scripts/run_all_tests.py --backend-unit  # Backend unit tests only
    python scripts/run_all_tests.py --backend-integration  # Backend integration tests
    python scripts/run_all_tests.py --frontend   # Frontend unit tests only
    python scripts/run_all_tests.py --frontend-e2e  # Frontend e2e tests only
    python scripts/run_all_tests.py --frontend --frontend-e2e  # All frontend tests
    python scripts/run_all_tests.py --coverage   # Run with coverage reports
    python scripts/run_all_tests.py --fail-fast  # Stop on first failure
    python scripts/run_all_tests.py --verbose    # Verbose output
    python scripts/run_all_tests.py --e2e-headed # Run e2e with visible browser
    python scripts/run_all_tests.py -P           # Run all test suites in parallel
"""

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable, Optional


# =============================================================================
# Configuration
# =============================================================================

# Get project root directory (parent of scripts/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


@dataclass
class TestResult:
    """Result of a test suite run."""

    name: str
    success: bool
    duration: float
    output: str
    return_code: int
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    failed_tests: list[str] = field(default_factory=list)


# =============================================================================
# Terminal Colors
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a header with formatting."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_failure(text: str) -> None:
    """Print failure message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


# =============================================================================
# Test Runners
# =============================================================================


def run_command(
    command: list[str],
    cwd: Path,
    env: Optional[dict] = None,
    stream: bool = True,
) -> tuple[int, str]:
    """Run a command and capture output.

    Args:
        command: Command to run
        cwd: Working directory
        env: Additional environment variables
        stream: If True, stream output to terminal in real-time.
                If False, capture silently (for parallel execution).

    Returns:
        Tuple of (return_code, captured_output)
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    # Use Popen to capture output
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=full_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line buffered
    )

    captured_output = []
    for line in process.stdout:
        if stream:
            print(line, end="")  # Stream to terminal
        captured_output.append(line)

    process.wait()
    return process.returncode, "".join(captured_output)


def parse_pytest_output(output: str) -> tuple[int, int, int, list[str]]:
    """Parse pytest output to extract test counts and failed test names.

    Returns:
        Tuple of (passed, failed, skipped, failed_test_names)
    """
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Parse pytest summary line like "5 passed, 2 failed, 1 skipped in 10.5s"
    # or "===== 5 passed in 10.5s =====" or "2 failed, 3 passed in 10.5s"
    # Look for lines containing " in " followed by time (indicating summary line)
    for line in output.split("\n"):
        # Summary lines typically end with "in X.XXs" pattern
        if re.search(r"\d+\.\d+s", line) and (
            " passed" in line or " failed" in line or " error" in line
        ):
            # Extract each count separately for robustness
            passed_match = re.search(r"(\d+)\s+passed", line)
            failed_match = re.search(r"(\d+)\s+failed", line)
            skipped_match = re.search(r"(\d+)\s+skipped", line)
            error_match = re.search(r"(\d+)\s+error", line)

            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if skipped_match:
                skipped = int(skipped_match.group(1))
            if error_match:
                # Count errors as failures
                failed += int(error_match.group(1))

    # Extract failed test names (FAILED tests/unit/test_foo.py::test_bar)
    failed_pattern = r"FAILED\s+([\w/._:-]+)"
    for match in re.finditer(failed_pattern, output):
        test_name = match.group(1)
        # Clean up the test name for display
        if "::" in test_name:
            # Extract just the test function name for cleaner display
            parts = test_name.split("::")
            if len(parts) >= 2:
                file_path = parts[0]
                test_func = parts[-1]
                # Shorten path: tests/unit/test_foo.py -> test_foo.py
                short_file = file_path.split("/")[-1] if "/" in file_path else file_path
                test_name = f"{short_file}::{test_func}"
        failed_tests.append(test_name)

    return passed, failed, skipped, failed_tests


def parse_vitest_output(output: str) -> tuple[int, int, int, list[str]]:
    """Parse vitest output to extract test counts and failed test names.

    Returns:
        Tuple of (passed, failed, skipped, failed_test_names)
    """
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Parse vitest summary: "Tests  5 passed | 2 failed | 1 skipped (8)"
    # or "Tests  5 passed (5)"
    tests_pattern = r"Tests\s+(?:(\d+)\s+passed)?\s*\|?\s*(?:(\d+)\s+failed)?\s*\|?\s*(?:(\d+)\s+skipped)?"
    for line in output.split("\n"):
        if "Tests" in line and ("passed" in line or "failed" in line):
            match = re.search(tests_pattern, line)
            if match:
                passed = int(match.group(1) or 0)
                failed = int(match.group(2) or 0)
                skipped = int(match.group(3) or 0)

    # Extract failed test names from vitest output
    # Pattern: "FAIL  src/components/Foo.test.jsx > Foo > should do something"
    # or "× should do something" preceded by describe block
    fail_pattern = r"(?:FAIL|×)\s+(.+)"
    for line in output.split("\n"):
        if line.strip().startswith("FAIL") or line.strip().startswith("×"):
            match = re.search(fail_pattern, line.strip())
            if match:
                test_name = match.group(1).strip()
                if test_name and test_name not in failed_tests:
                    failed_tests.append(test_name)

    return passed, failed, skipped, failed_tests


def parse_playwright_output(output: str) -> tuple[int, int, int, list[str]]:
    """Parse Playwright output to extract test counts and failed test names.

    Returns:
        Tuple of (passed, failed, skipped, failed_test_names)
    """
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Parse Playwright summary: "5 passed (10s)" or "2 failed, 3 passed (15s)"
    # Format: "X passed" or "X failed"
    for line in output.split("\n"):
        if "passed" in line or "failed" in line:
            passed_match = re.search(r"(\d+)\s+passed", line)
            failed_match = re.search(r"(\d+)\s+failed", line)
            skipped_match = re.search(r"(\d+)\s+skipped", line)
            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if skipped_match:
                skipped = int(skipped_match.group(1))

    # Extract failed test names
    # Pattern varies, but often "1) [chromium] › e2e/test.spec.js:10:5 › test name"
    fail_pattern = r"\d+\)\s+\[[\w]+\]\s+›\s+(.+)"
    for line in output.split("\n"):
        match = re.search(fail_pattern, line)
        if match:
            test_info = match.group(1).strip()
            if test_info and test_info not in failed_tests:
                failed_tests.append(test_info)

    return passed, failed, skipped, failed_tests


def run_backend_unit_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
    parallel: bool = False,
    stream: bool = True,
) -> TestResult:
    """Run backend unit tests."""
    if stream:
        print_header("Backend Unit Tests")

    start_time = time.time()

    command = ["python", "-m", "pytest", "tests/unit/"]

    if verbose:
        command.append("-v")
    else:
        command.append("-q")

    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing"])

    if fail_fast:
        command.append("-x")

    if parallel:
        command.extend(["-n", "auto"])  # Requires pytest-xdist

    if stream:
        print_info(f"Running: {' '.join(command)}")
        print_info(f"Working directory: {BACKEND_DIR}\n")

    return_code, output = run_command(command, BACKEND_DIR, stream=stream)

    duration = time.time() - start_time
    success = return_code == 0

    # Parse test results
    passed, failed, skipped, failed_tests = parse_pytest_output(output)

    if stream:
        if success:
            print_success(f"Backend unit tests passed ({duration:.2f}s)")
        else:
            print_failure(f"Backend unit tests failed ({duration:.2f}s)")

    return TestResult(
        name="Backend Unit Tests",
        success=success,
        duration=duration,
        output=output,
        return_code=return_code,
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
        failed_tests=failed_tests,
    )


def run_backend_integration_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
    stream: bool = True,
) -> TestResult:
    """Run backend integration tests."""
    if stream:
        print_header("Backend Integration Tests")

    start_time = time.time()

    command = ["python", "-m", "pytest", "tests/integration/"]

    if verbose:
        command.append("-v")
    else:
        command.append("-q")

    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing", "--cov-append"])

    if fail_fast:
        command.append("-x")

    if stream:
        print_info(f"Running: {' '.join(command)}")
        print_info(f"Working directory: {BACKEND_DIR}")
        print_warning(
            "Integration tests require running services (PostgreSQL, Redis, Neo4j)\n"
        )

    return_code, output = run_command(command, BACKEND_DIR, stream=stream)

    duration = time.time() - start_time
    success = return_code == 0

    # Parse test results
    passed, failed, skipped, failed_tests = parse_pytest_output(output)

    if stream:
        if success:
            print_success(f"Backend integration tests passed ({duration:.2f}s)")
        else:
            print_failure(f"Backend integration tests failed ({duration:.2f}s)")

    return TestResult(
        name="Backend Integration Tests",
        success=success,
        duration=duration,
        output=output,
        return_code=return_code,
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
        failed_tests=failed_tests,
    )


def run_frontend_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
    stream: bool = True,
) -> TestResult:
    """Run frontend unit tests."""
    if stream:
        print_header("Frontend Unit Tests")

    # Check if frontend test script exists
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        if stream:
            print_warning("Frontend package.json not found, skipping frontend tests")
        return TestResult(
            name="Frontend Unit Tests",
            success=True,
            duration=0,
            output="Skipped - no package.json",
            return_code=0,
        )

    # Check if test script is configured
    import json

    with open(package_json) as f:
        pkg = json.load(f)

    scripts = pkg.get("scripts", {})
    if "test" not in scripts:
        if stream:
            print_warning("No 'test' script in package.json, skipping frontend tests")
            print_info(
                "To enable frontend tests, add a 'test' script to frontend/package.json"
            )
            print_info('Example: "test": "vitest run"')
        return TestResult(
            name="Frontend Unit Tests",
            success=True,
            duration=0,
            output="Skipped - no test script configured",
            return_code=0,
        )

    start_time = time.time()

    # Build command based on test runner
    test_script = scripts.get("test", "")

    if coverage and "test:coverage" in scripts:
        command = ["npm", "run", "test:coverage"]
    else:
        command = ["npm", "test"]

    # Add run flag for non-watch mode (vitest)
    if "vitest" in test_script and "run" not in test_script:
        command.extend(["--", "--run"])

    if fail_fast:
        command.extend(["--", "--bail"] if "--" not in command else ["--bail"])

    if stream:
        print_info(f"Running: {' '.join(command)}")
        print_info(f"Working directory: {FRONTEND_DIR}\n")

    return_code, output = run_command(command, FRONTEND_DIR, stream=stream)

    duration = time.time() - start_time
    success = return_code == 0

    # Parse test results (vitest format)
    passed, failed, skipped, failed_tests = parse_vitest_output(output)

    if stream:
        if success:
            print_success(f"Frontend unit tests passed ({duration:.2f}s)")
        else:
            print_failure(f"Frontend unit tests failed ({duration:.2f}s)")

    return TestResult(
        name="Frontend Unit Tests",
        success=success,
        duration=duration,
        output=output,
        return_code=return_code,
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
        failed_tests=failed_tests,
    )


def run_frontend_e2e_tests(
    verbose: bool = False,
    fail_fast: bool = False,
    headed: bool = False,
    stream: bool = True,
) -> TestResult:
    """Run frontend e2e tests with Playwright."""
    if stream:
        print_header("Frontend E2E Tests (Playwright)")

    # Check if frontend test script exists
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        if stream:
            print_warning("Frontend package.json not found, skipping e2e tests")
        return TestResult(
            name="Frontend E2E Tests",
            success=True,
            duration=0,
            output="Skipped - no package.json",
            return_code=0,
        )

    # Check if e2e test script is configured
    import json

    with open(package_json) as f:
        pkg = json.load(f)

    scripts = pkg.get("scripts", {})
    if "test:e2e" not in scripts:
        if stream:
            print_warning("No 'test:e2e' script in package.json, skipping e2e tests")
            print_info(
                "To enable e2e tests, add 'test:e2e': 'playwright test' to frontend/package.json"
            )
        return TestResult(
            name="Frontend E2E Tests",
            success=True,
            duration=0,
            output="Skipped - no test:e2e script configured",
            return_code=0,
        )

    # Check if playwright config exists
    playwright_config = FRONTEND_DIR / "playwright.config.js"
    if not playwright_config.exists():
        if stream:
            print_warning("No playwright.config.js found, skipping e2e tests")
        return TestResult(
            name="Frontend E2E Tests",
            success=True,
            duration=0,
            output="Skipped - no playwright.config.js",
            return_code=0,
        )

    start_time = time.time()

    # Build command
    if headed:
        command = ["npm", "run", "test:e2e:headed"]
    else:
        command = ["npm", "run", "test:e2e"]

    if stream:
        print_info(f"Running: {' '.join(command)}")
        print_info(f"Working directory: {FRONTEND_DIR}")
        print_warning("E2E tests will start the dev server automatically\n")

    return_code, output = run_command(command, FRONTEND_DIR, stream=stream)

    duration = time.time() - start_time
    success = return_code == 0

    # Parse test results (playwright format)
    passed, failed, skipped, failed_tests = parse_playwright_output(output)

    if stream:
        if success:
            print_success(f"Frontend e2e tests passed ({duration:.2f}s)")
        else:
            print_failure(f"Frontend e2e tests failed ({duration:.2f}s)")
            print_info(
                "Run 'npm run test:e2e:report' in frontend/ to view detailed report"
            )

    return TestResult(
        name="Frontend E2E Tests",
        success=success,
        duration=duration,
        output=output,
        return_code=return_code,
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
        failed_tests=failed_tests,
    )


# =============================================================================
# Summary Report
# =============================================================================


def print_summary(results: list[TestResult]) -> bool:
    """Print test summary and return overall success status."""
    print_header("Test Summary")

    total_duration = sum(r.duration for r in results)
    all_passed = all(r.success for r in results)

    # Aggregate totals
    total_passed = sum(r.passed_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    total_skipped = sum(r.skipped_count for r in results)
    all_failed_tests: list[tuple[str, str]] = []  # (suite_name, test_name)

    # Print individual results with counts
    for result in results:
        status = (
            f"{Colors.GREEN}PASSED{Colors.END}"
            if result.success
            else f"{Colors.RED}FAILED{Colors.END}"
        )

        # Build counts string
        counts_parts = []
        if result.passed_count > 0:
            counts_parts.append(
                f"{Colors.GREEN}{result.passed_count} passed{Colors.END}"
            )
        if result.failed_count > 0:
            counts_parts.append(f"{Colors.RED}{result.failed_count} failed{Colors.END}")
        if result.skipped_count > 0:
            counts_parts.append(
                f"{Colors.YELLOW}{result.skipped_count} skipped{Colors.END}"
            )

        counts_str = ", ".join(counts_parts) if counts_parts else "no tests found"

        print(f"  {result.name:<30} {status}  ({result.duration:.2f}s)")
        print(f"    {counts_str}")

        # Collect failed tests
        for test_name in result.failed_tests:
            all_failed_tests.append((result.name, test_name))

    print()
    print(f"  {'─' * 60}")

    # Print totals
    total_tests = total_passed + total_failed + total_skipped
    print(f"  {Colors.BOLD}Total:{Colors.END} {total_tests} tests")
    print(f"    {Colors.GREEN}✓ {total_passed} passed{Colors.END}")
    if total_failed > 0:
        print(f"    {Colors.RED}✗ {total_failed} failed{Colors.END}")
    if total_skipped > 0:
        print(f"    {Colors.YELLOW}○ {total_skipped} skipped{Colors.END}")
    print(f"  {Colors.BOLD}Time:{Colors.END} {total_duration:.2f}s")

    # Print failed tests list
    if all_failed_tests:
        print()
        print(f"  {Colors.RED}{Colors.BOLD}Failed Tests:{Colors.END}")
        for suite_name, test_name in all_failed_tests:
            # Shorten suite name for display
            short_suite = (
                suite_name.replace(" Tests", "")
                .replace("Backend ", "BE ")
                .replace("Frontend ", "FE ")
            )
            print(f"    {Colors.RED}✗{Colors.END} [{short_suite}] {test_name}")

    print()

    if all_passed:
        print_success("All test suites passed! 🎉")
    else:
        failed_suite_count = sum(1 for r in results if not r.success)
        print_failure(
            f"{failed_suite_count} test suite(s) failed with {total_failed} failing test(s)"
        )

    return all_passed


# =============================================================================
# Main Entry Point
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run all tests for the Second Brain project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_all_tests.py                    # Run all tests (backend + frontend unit/e2e)
  python scripts/run_all_tests.py --backend-unit     # Backend unit tests only
  python scripts/run_all_tests.py --backend          # All backend tests
  python scripts/run_all_tests.py --frontend         # Frontend unit tests only
  python scripts/run_all_tests.py --frontend-e2e     # Frontend e2e tests only
  python scripts/run_all_tests.py --frontend --frontend-e2e  # All frontend tests
  python scripts/run_all_tests.py --coverage         # Run with coverage
  python scripts/run_all_tests.py -v --fail-fast     # Verbose, stop on failure
  python scripts/run_all_tests.py --frontend-e2e --e2e-headed  # E2E with browser
  python scripts/run_all_tests.py -P                 # Run all suites in parallel (faster)
        """,
    )

    # Test selection
    selection = parser.add_argument_group("Test Selection")
    selection.add_argument(
        "--backend-unit",
        action="store_true",
        help="Run backend unit tests only",
    )
    selection.add_argument(
        "--backend-integration",
        action="store_true",
        help="Run backend integration tests only",
    )
    selection.add_argument(
        "--backend",
        action="store_true",
        help="Run all backend tests (unit + integration)",
    )
    selection.add_argument(
        "--frontend",
        action="store_true",
        help="Run frontend unit tests only",
    )
    selection.add_argument(
        "--frontend-e2e",
        action="store_true",
        help="Run frontend e2e tests (Playwright)",
    )

    # Options
    options = parser.add_argument_group("Options")
    options.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    options.add_argument(
        "-c",
        "--coverage",
        action="store_true",
        help="Run with coverage reports",
    )
    options.add_argument(
        "-x",
        "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )
    options.add_argument(
        "-p",
        "--parallel",
        action="store_true",
        help="Run pytest tests in parallel within suite (requires pytest-xdist)",
    )
    options.add_argument(
        "-P",
        "--parallel-suites",
        action="store_true",
        help="Run test suites in parallel (faster but interleaved output)",
    )
    options.add_argument(
        "--e2e-headed",
        action="store_true",
        help="Run e2e tests with visible browser (requires --frontend-e2e)",
    )

    return parser.parse_args()


def run_suites_parallel(
    suite_funcs: list[tuple[str, Callable[[], TestResult]]],
) -> list[TestResult]:
    """Run test suites in parallel and return results.

    Args:
        suite_funcs: List of (name, callable) tuples for test suites to run

    Returns:
        List of TestResult in the same order as suite_funcs
    """
    results: dict[str, TestResult] = {}
    print_lock = Lock()

    def run_suite(name: str, func: Callable[[], TestResult]) -> tuple[str, TestResult]:
        """Run a single test suite."""
        result = func()

        # Print completion notification with lock
        with print_lock:
            status = (
                f"{Colors.GREEN}✓{Colors.END}"
                if result.success
                else f"{Colors.RED}✗{Colors.END}"
            )
            print(f"\n{status} {name} completed ({result.duration:.2f}s) - ", end="")
            if result.success:
                print(f"{Colors.GREEN}{result.passed_count} passed{Colors.END}")
            else:
                print(
                    f"{Colors.RED}{result.failed_count} failed{Colors.END}, {Colors.GREEN}{result.passed_count} passed{Colors.END}"
                )

        return name, result

    print_info(f"Running {len(suite_funcs)} test suites in parallel...\n")

    # Run all suites in parallel
    with ThreadPoolExecutor(max_workers=len(suite_funcs)) as executor:
        futures = {
            executor.submit(run_suite, name, func): name for name, func in suite_funcs
        }

        for future in as_completed(futures):
            name, result = future.result()
            results[name] = result

    # Return results in original order
    return [results[name] for name, _ in suite_funcs]


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Check if any specific test suite was requested
    specific_tests_requested = any(
        [
            args.backend_unit,
            args.backend_integration,
            args.backend,
            args.frontend,
            args.frontend_e2e,
        ]
    )

    # Determine which tests to run
    # By default, run all tests (backend unit/integration + frontend unit/e2e)
    run_backend_unit = args.backend_unit or args.backend or not specific_tests_requested
    run_backend_int = (
        args.backend_integration or args.backend or not specific_tests_requested
    )
    run_frontend = args.frontend or not specific_tests_requested
    run_frontend_e2e = args.frontend_e2e or not specific_tests_requested

    print_header("Second Brain Test Runner")
    print_info(f"Project root: {PROJECT_ROOT}")
    print_info(f"Backend unit tests: {run_backend_unit}")
    print_info(f"Backend integration tests: {run_backend_int}")
    print_info(f"Frontend unit tests: {run_frontend}")
    print_info(f"Frontend e2e tests: {run_frontend_e2e}")
    if args.parallel_suites:
        print_info(f"{Colors.CYAN}Running test suites in PARALLEL mode{Colors.END}")

    results: list[TestResult] = []

    # Build list of test suites to run
    if args.parallel_suites:
        # Parallel execution - no streaming, collect results at end
        suite_funcs: list[tuple[str, Callable[[], TestResult]]] = []

        if run_backend_unit:
            suite_funcs.append(
                (
                    "Backend Unit Tests",
                    lambda: run_backend_unit_tests(
                        verbose=args.verbose,
                        coverage=args.coverage,
                        fail_fast=args.fail_fast,
                        parallel=args.parallel,
                        stream=False,
                    ),
                )
            )

        if run_backend_int:
            suite_funcs.append(
                (
                    "Backend Integration Tests",
                    lambda: run_backend_integration_tests(
                        verbose=args.verbose,
                        coverage=args.coverage,
                        fail_fast=args.fail_fast,
                        stream=False,
                    ),
                )
            )

        if run_frontend:
            suite_funcs.append(
                (
                    "Frontend Unit Tests",
                    lambda: run_frontend_tests(
                        verbose=args.verbose,
                        coverage=args.coverage,
                        fail_fast=args.fail_fast,
                        stream=False,
                    ),
                )
            )

        if run_frontend_e2e:
            suite_funcs.append(
                (
                    "Frontend E2E Tests",
                    lambda: run_frontend_e2e_tests(
                        verbose=args.verbose,
                        fail_fast=args.fail_fast,
                        headed=args.e2e_headed,
                        stream=False,
                    ),
                )
            )

        if suite_funcs:
            results = run_suites_parallel(suite_funcs)
    else:
        # Sequential execution - streaming output
        if run_backend_unit:
            result = run_backend_unit_tests(
                verbose=args.verbose,
                coverage=args.coverage,
                fail_fast=args.fail_fast,
                parallel=args.parallel,
            )
            results.append(result)

            if args.fail_fast and not result.success:
                print_summary(results)
                return 1

        if run_backend_int:
            result = run_backend_integration_tests(
                verbose=args.verbose,
                coverage=args.coverage,
                fail_fast=args.fail_fast,
            )
            results.append(result)

            if args.fail_fast and not result.success:
                print_summary(results)
                return 1

        if run_frontend:
            result = run_frontend_tests(
                verbose=args.verbose,
                coverage=args.coverage,
                fail_fast=args.fail_fast,
            )
            results.append(result)

            if args.fail_fast and not result.success:
                print_summary(results)
                return 1

        if run_frontend_e2e:
            result = run_frontend_e2e_tests(
                verbose=args.verbose,
                fail_fast=args.fail_fast,
                headed=args.e2e_headed,
            )
            results.append(result)

    # Print summary
    all_passed = print_summary(results)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
