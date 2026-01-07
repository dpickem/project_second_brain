"""
Docker Code Sandbox Manager

Secure Docker-based sandbox for executing learner-submitted code
with strict resource limits to prevent:
- Resource exhaustion (CPU, memory, disk)
- Network access (data exfiltration)
- File system access (reading secrets)
- Long-running processes (DoS)

Usage:
    from app.services.learning.code_sandbox import CodeSandbox

    sandbox = CodeSandbox()

    # Execute code
    result = await sandbox.execute_code(
        code="print('Hello')",
        language="python",
    )

    # Run tests
    test_results = await sandbox.run_tests(
        code="def solution(x): return x * 2",
        test_cases=[{"input": "5", "expected": "10"}],
        language="python",
    )
"""

import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docker
from docker.errors import APIError, ContainerError, ImageNotFound

from app.config.settings import get_settings
from app.models.learning import CodeExecutionResult

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ExecutionResult:
    """Result of code execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    error: Optional[str] = None


# Language configuration: image, extension, command
LANGUAGE_CONFIG = {
    "python": {
        "image": "python:3.11-slim",
        "extension": ".py",
        "command": ["python3"],
    },
    "pytorch": {
        "image": "python:3.11-slim",  # Use slim image, install torch if needed
        "extension": ".py",
        "command": ["python3"],
    },
    "javascript": {
        "image": "node:20-alpine",
        "extension": ".js",
        "command": ["node"],
    },
    "typescript": {
        "image": "node:20-alpine",
        "extension": ".ts",
        "command": ["npx", "ts-node"],
    },
}


# Test wrapper templates for each language
TEST_WRAPPERS = {
    "python": """
{code}

# Test harness
import json
import sys

def _run_test(input_val, expected):
    try:
        result = solution(input_val)
        result_str = str(result) if not isinstance(result, str) else result
        expected_str = str(expected) if not isinstance(expected, str) else expected
        passed = result_str.strip() == expected_str.strip()
        return {{"passed": passed, "actual": result_str, "expected": expected_str}}
    except Exception as e:
        return {{"passed": False, "actual": str(e), "expected": expected_str, "error": str(e)}}

test_input = {test_input}
expected_output = {expected_output}
result = _run_test(test_input, expected_output)
print(json.dumps(result))
""",
    "javascript": """
{code}

// Test harness
const testInput = {test_input};
const expectedOutput = {expected_output};

try {{
    const result = solution(testInput);
    const resultStr = String(result).trim();
    const expectedStr = String(expectedOutput).trim();
    const passed = resultStr === expectedStr;
    console.log(JSON.stringify({{passed, actual: resultStr, expected: expectedStr}}));
}} catch (e) {{
    console.log(JSON.stringify({{passed: false, actual: e.message, expected: expectedStr, error: e.message}}));
}}
""",
}


class CodeSandbox:
    """
    Secure Docker sandbox for code execution.

    Security features:
    - Memory limit (128MB)
    - CPU quota (50% of one core)
    - Network disabled
    - Read-only filesystem (except /tmp)
    - Non-root user
    - Process limit (50 max)
    - Execution timeout (10s)
    """

    # Security limits
    DEFAULT_TIMEOUT = 10  # seconds
    MEMORY_LIMIT = "128m"
    CPU_QUOTA = 50000  # 50% of one core
    MAX_PIDS = 50

    def __init__(
        self,
        timeout: Optional[int] = None,
        enabled: bool = True,
    ):
        """
        Initialize code sandbox.

        Args:
            timeout: Execution timeout in seconds
            enabled: Whether sandbox is enabled
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.enabled = enabled
        self.docker_client: Optional[docker.DockerClient] = None

        if self.enabled:
            try:
                self.docker_client = docker.from_env()
                self.docker_client.ping()
                logger.info("Docker sandbox initialized successfully")
            except Exception as e:
                logger.warning(f"Docker not available: {e}")
                self.enabled = False

    async def execute_code(
        self,
        code: str,
        language: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute code in a secure sandbox.

        Args:
            code: Code to execute
            language: Programming language
            timeout: Optional timeout override

        Returns:
            Execution result
        """
        if not self.enabled:
            return ExecutionResult(
                success=False,
                error="Code sandbox is not enabled",
            )

        language = language.lower()
        if language not in LANGUAGE_CONFIG:
            return ExecutionResult(
                success=False,
                error=f"Unsupported language: {language}",
            )

        config = LANGUAGE_CONFIG[language]
        timeout = timeout or self.timeout

        # Create temporary directory for code
        temp_dir = tempfile.mkdtemp(prefix="sandbox_")

        try:
            # Write code to file
            code_file = Path(temp_dir) / f"code{config['extension']}"
            code_file.write_text(code)

            # Build command
            command = config["command"] + [f"/code/code{config['extension']}"]

            # Run in container
            result = await self._run_container(
                image=config["image"],
                command=command,
                code_dir=temp_dir,
                timeout=timeout,
            )

            return result

        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")

    async def run_tests(
        self,
        code: str,
        test_cases: list[dict],
        language: str,
    ) -> list[CodeExecutionResult]:
        """
        Run test cases against learner code.

        Args:
            code: Learner's code (should define a `solution` function)
            test_cases: List of test cases with input/expected
            language: Programming language

        Returns:
            List of test results
        """
        if not self.enabled:
            return [
                CodeExecutionResult(
                    test_index=i,
                    passed=False,
                    error="Code sandbox is not enabled",
                )
                for i in range(len(test_cases))
            ]

        results = []

        for i, test_case in enumerate(test_cases):
            test_code = self._create_test_wrapper(
                code=code,
                test_input=test_case.get("input", ""),
                expected_output=test_case.get("expected", ""),
                language=language,
            )

            exec_result = await self.execute_code(test_code, language)

            if exec_result.success and exec_result.stdout:
                # Parse JSON result from test harness
                try:
                    result_data = json.loads(exec_result.stdout.strip())
                    results.append(
                        CodeExecutionResult(
                            test_index=i,
                            passed=result_data.get("passed", False),
                            input_value=str(test_case.get("input", "")),
                            expected=result_data.get("expected", ""),
                            actual=result_data.get("actual", ""),
                            error=result_data.get("error"),
                        )
                    )
                except json.JSONDecodeError:
                    results.append(
                        CodeExecutionResult(
                            test_index=i,
                            passed=False,
                            input_value=str(test_case.get("input", "")),
                            expected=str(test_case.get("expected", "")),
                            actual=exec_result.stdout,
                            error="Failed to parse test output",
                        )
                    )
            else:
                # Execution failed
                error_msg = exec_result.error or exec_result.stderr
                if exec_result.timed_out:
                    error_msg = "Execution timed out"

                results.append(
                    CodeExecutionResult(
                        test_index=i,
                        passed=False,
                        input_value=str(test_case.get("input", "")),
                        expected=str(test_case.get("expected", "")),
                        error=error_msg,
                    )
                )

        return results

    async def _run_container(
        self,
        image: str,
        command: list[str],
        code_dir: str,
        timeout: int,
    ) -> ExecutionResult:
        """
        Run code in a Docker container with security limits.

        Args:
            image: Docker image to use
            command: Command to execute
            code_dir: Directory containing code
            timeout: Execution timeout

        Returns:
            Execution result
        """
        container = None

        try:
            # Ensure image is available
            try:
                self.docker_client.images.get(image)
            except ImageNotFound:
                logger.info(f"Pulling image {image}...")
                self.docker_client.images.pull(image)

            # Create container with security limits
            container = self.docker_client.containers.create(
                image=image,
                command=command,
                volumes={
                    code_dir: {"bind": "/code", "mode": "ro"},  # Read-only
                },
                working_dir="/code",
                # Security limits
                mem_limit=self.MEMORY_LIMIT,
                memswap_limit=self.MEMORY_LIMIT,  # No swap
                cpu_quota=self.CPU_QUOTA,
                network_disabled=True,
                read_only=True,  # Read-only root filesystem
                pids_limit=self.MAX_PIDS,
                # Minimal capabilities
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                # Temporary writable directory
                tmpfs={"/tmp": "size=10m,mode=1777"},
                # Non-root user (if image supports it)
                user="nobody" if "python" in image or "node" in image else None,
            )

            # Run with timeout
            container.start()

            # Wait for completion with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, container.wait),
                    timeout=timeout,
                )
                exit_code = result.get("StatusCode", 1)
                timed_out = False
            except asyncio.TimeoutError:
                # Kill container on timeout
                try:
                    container.kill()
                except Exception:
                    pass
                exit_code = -1
                timed_out = True

            # Get logs
            logs = container.logs(stdout=True, stderr=True)
            stdout = ""
            stderr = ""

            if isinstance(logs, bytes):
                # Combined output
                stdout = logs.decode("utf-8", errors="replace")
            else:
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8", errors="replace"
                )
                stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8", errors="replace"
                )

            return ExecutionResult(
                success=exit_code == 0 and not timed_out,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
            )

        except ContainerError as e:
            return ExecutionResult(
                success=False,
                stderr=str(e.stderr) if e.stderr else "",
                exit_code=e.exit_status,
                error=str(e),
            )
        except APIError as e:
            logger.error(f"Docker API error: {e}")
            return ExecutionResult(
                success=False,
                error=f"Docker error: {e}",
            )
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
            )
        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

    def _create_test_wrapper(
        self,
        code: str,
        test_input: str,
        expected_output: str,
        language: str,
    ) -> str:
        """
        Create code with test harness wrapper.

        Args:
            code: Learner's code
            test_input: Test input value
            expected_output: Expected output
            language: Programming language

        Returns:
            Code with test harness
        """
        language = language.lower()

        # Get wrapper template
        wrapper = TEST_WRAPPERS.get(language, TEST_WRAPPERS["python"])

        # Format test values - try to parse as JSON for proper typing
        try:
            test_input_formatted = json.dumps(json.loads(test_input))
        except (json.JSONDecodeError, TypeError):
            test_input_formatted = repr(test_input)

        try:
            expected_formatted = json.dumps(json.loads(expected_output))
        except (json.JSONDecodeError, TypeError):
            expected_formatted = repr(expected_output)

        return wrapper.format(
            code=code,
            test_input=test_input_formatted,
            expected_output=expected_formatted,
        )


# Singleton instance
_sandbox_instance: Optional[CodeSandbox] = None


def get_code_sandbox() -> CodeSandbox:
    """Get or create the code sandbox singleton."""
    global _sandbox_instance

    if _sandbox_instance is None:
        _sandbox_instance = CodeSandbox(
            timeout=getattr(settings, "SANDBOX_TIMEOUT_SECONDS", 10),
            enabled=getattr(settings, "SANDBOX_ENABLED", True),
        )

    return _sandbox_instance
