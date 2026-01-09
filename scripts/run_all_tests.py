#!/usr/bin/env python3
"""
Run All Tests - Unified Test Runner for Second Brain

This script runs all tests across the project:
- Backend unit tests (Python/pytest)
- Backend integration tests (Python/pytest)
- Frontend unit tests (JavaScript/Vitest)
- Frontend e2e tests (JavaScript/Playwright)

Usage:
    python scripts/run_all_tests.py              # Run all tests (excludes e2e by default)
    python scripts/run_all_tests.py --backend-unit  # Backend unit tests only
    python scripts/run_all_tests.py --backend-integration  # Backend integration tests
    python scripts/run_all_tests.py --frontend   # Frontend unit tests only
    python scripts/run_all_tests.py --frontend-e2e  # Frontend e2e tests only
    python scripts/run_all_tests.py --frontend --frontend-e2e  # All frontend tests
    python scripts/run_all_tests.py --coverage   # Run with coverage reports
    python scripts/run_all_tests.py --fail-fast  # Stop on first failure
    python scripts/run_all_tests.py --verbose    # Verbose output
    python scripts/run_all_tests.py --e2e-headed # Run e2e with visible browser
"""

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    return subprocess.run(
        command,
        cwd=cwd,
        env=full_env,
        capture_output=capture_output,
        text=True,
    )


def run_backend_unit_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
    parallel: bool = False,
) -> TestResult:
    """Run backend unit tests."""
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
    
    print_info(f"Running: {' '.join(command)}")
    print_info(f"Working directory: {BACKEND_DIR}\n")
    
    result = run_command(command, BACKEND_DIR)
    
    duration = time.time() - start_time
    success = result.returncode == 0
    
    if success:
        print_success(f"Backend unit tests passed ({duration:.2f}s)")
    else:
        print_failure(f"Backend unit tests failed ({duration:.2f}s)")
    
    return TestResult(
        name="Backend Unit Tests",
        success=success,
        duration=duration,
        output=result.stdout if hasattr(result, 'stdout') and result.stdout else "",
        return_code=result.returncode,
    )


def run_backend_integration_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
) -> TestResult:
    """Run backend integration tests."""
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
    
    print_info(f"Running: {' '.join(command)}")
    print_info(f"Working directory: {BACKEND_DIR}")
    print_warning("Integration tests require running services (PostgreSQL, Redis, Neo4j)\n")
    
    result = run_command(command, BACKEND_DIR)
    
    duration = time.time() - start_time
    success = result.returncode == 0
    
    if success:
        print_success(f"Backend integration tests passed ({duration:.2f}s)")
    else:
        print_failure(f"Backend integration tests failed ({duration:.2f}s)")
    
    return TestResult(
        name="Backend Integration Tests",
        success=success,
        duration=duration,
        output=result.stdout if hasattr(result, 'stdout') and result.stdout else "",
        return_code=result.returncode,
    )


def run_frontend_tests(
    verbose: bool = False,
    coverage: bool = False,
    fail_fast: bool = False,
) -> TestResult:
    """Run frontend unit tests."""
    print_header("Frontend Unit Tests")
    
    # Check if frontend test script exists
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
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
        print_warning("No 'test' script in package.json, skipping frontend tests")
        print_info("To enable frontend tests, add a 'test' script to frontend/package.json")
        print_info("Example: \"test\": \"vitest run\"")
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
    
    print_info(f"Running: {' '.join(command)}")
    print_info(f"Working directory: {FRONTEND_DIR}\n")
    
    result = run_command(command, FRONTEND_DIR)
    
    duration = time.time() - start_time
    success = result.returncode == 0
    
    if success:
        print_success(f"Frontend unit tests passed ({duration:.2f}s)")
    else:
        print_failure(f"Frontend unit tests failed ({duration:.2f}s)")
    
    return TestResult(
        name="Frontend Unit Tests",
        success=success,
        duration=duration,
        output=result.stdout if hasattr(result, 'stdout') and result.stdout else "",
        return_code=result.returncode,
    )


def run_frontend_e2e_tests(
    verbose: bool = False,
    fail_fast: bool = False,
    headed: bool = False,
) -> TestResult:
    """Run frontend e2e tests with Playwright."""
    print_header("Frontend E2E Tests (Playwright)")
    
    # Check if frontend test script exists
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
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
        print_warning("No 'test:e2e' script in package.json, skipping e2e tests")
        print_info("To enable e2e tests, add 'test:e2e': 'playwright test' to frontend/package.json")
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
    
    print_info(f"Running: {' '.join(command)}")
    print_info(f"Working directory: {FRONTEND_DIR}")
    print_warning("E2E tests will start the dev server automatically\n")
    
    result = run_command(command, FRONTEND_DIR)
    
    duration = time.time() - start_time
    success = result.returncode == 0
    
    if success:
        print_success(f"Frontend e2e tests passed ({duration:.2f}s)")
    else:
        print_failure(f"Frontend e2e tests failed ({duration:.2f}s)")
        print_info("Run 'npm run test:e2e:report' in frontend/ to view detailed report")
    
    return TestResult(
        name="Frontend E2E Tests",
        success=success,
        duration=duration,
        output=result.stdout if hasattr(result, 'stdout') and result.stdout else "",
        return_code=result.returncode,
    )


# =============================================================================
# Summary Report
# =============================================================================

def print_summary(results: list[TestResult]) -> bool:
    """Print test summary and return overall success status."""
    print_header("Test Summary")
    
    total_duration = sum(r.duration for r in results)
    all_passed = all(r.success for r in results)
    
    # Print individual results
    for result in results:
        status = f"{Colors.GREEN}PASSED{Colors.END}" if result.success else f"{Colors.RED}FAILED{Colors.END}"
        print(f"  {result.name:<30} {status}  ({result.duration:.2f}s)")
    
    print()
    print(f"  {'─' * 50}")
    print(f"  Total time: {total_duration:.2f}s")
    print()
    
    if all_passed:
        print_success("All test suites passed! 🎉")
    else:
        failed_count = sum(1 for r in results if not r.success)
        print_failure(f"{failed_count} test suite(s) failed")
    
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
  python scripts/run_all_tests.py                    # Run all tests (excludes e2e)
  python scripts/run_all_tests.py --backend-unit     # Backend unit tests only
  python scripts/run_all_tests.py --backend          # All backend tests
  python scripts/run_all_tests.py --frontend         # Frontend unit tests only
  python scripts/run_all_tests.py --frontend-e2e     # Frontend e2e tests only
  python scripts/run_all_tests.py --frontend --frontend-e2e  # All frontend tests
  python scripts/run_all_tests.py --coverage         # Run with coverage
  python scripts/run_all_tests.py -v --fail-fast     # Verbose, stop on failure
  python scripts/run_all_tests.py --frontend-e2e --e2e-headed  # E2E with browser
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
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    options.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage reports",
    )
    options.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )
    options.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)",
    )
    options.add_argument(
        "--e2e-headed",
        action="store_true",
        help="Run e2e tests with visible browser (requires --frontend-e2e)",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Check if any specific test suite was requested
    specific_tests_requested = any([
        args.backend_unit, args.backend_integration, args.backend, 
        args.frontend, args.frontend_e2e
    ])
    
    # Determine which tests to run
    # By default, run backend + frontend unit tests (NOT e2e - those are opt-in)
    run_backend_unit = args.backend_unit or args.backend or not specific_tests_requested
    run_backend_int = args.backend_integration or args.backend or not specific_tests_requested
    run_frontend = args.frontend or not specific_tests_requested
    run_frontend_e2e = args.frontend_e2e  # E2E is always opt-in
    
    print_header("Second Brain Test Runner")
    print_info(f"Project root: {PROJECT_ROOT}")
    print_info(f"Backend unit tests: {run_backend_unit}")
    print_info(f"Backend integration tests: {run_backend_int}")
    print_info(f"Frontend unit tests: {run_frontend}")
    print_info(f"Frontend e2e tests: {run_frontend_e2e}")
    
    results: list[TestResult] = []
    
    # Run selected tests
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
