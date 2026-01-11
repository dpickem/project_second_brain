"""
Unit tests for Code Sandbox.

Tests the Docker-based code execution sandbox functionality.
Note: Some tests require Docker to be available and will be skipped if not.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.learning.code_sandbox import (
    CodeSandbox,
    ExecutionResult,
    LANGUAGE_CONFIG,
    TEST_WRAPPERS,
    get_code_sandbox,
)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            stdout="Hello, World!",
            exit_code=0,
        )
        assert result.success is True
        assert result.stdout == "Hello, World!"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.timed_out is False

    def test_failure_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            success=False,
            stderr="SyntaxError: invalid syntax",
            exit_code=1,
            error="Compilation failed",
        )
        assert result.success is False
        assert result.exit_code == 1
        assert result.error == "Compilation failed"

    def test_timeout_result(self):
        """Test timeout execution result."""
        result = ExecutionResult(
            success=False,
            timed_out=True,
            exit_code=-1,
        )
        assert result.timed_out is True
        assert result.exit_code == -1


class TestLanguageConfig:
    """Tests for language configuration."""

    def test_python_config(self):
        """Test Python language config exists."""
        assert "python" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["python"]
        assert "image" in config
        assert "extension" in config
        assert "command" in config
        assert config["extension"] == ".py"

    def test_javascript_config(self):
        """Test JavaScript language config exists."""
        assert "javascript" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["javascript"]
        assert config["extension"] == ".js"

    def test_typescript_config(self):
        """Test TypeScript language config exists."""
        assert "typescript" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["typescript"]
        assert config["extension"] == ".ts"


class TestTestWrappers:
    """Tests for test wrapper templates."""

    def test_python_wrapper_exists(self):
        """Test Python test wrapper template exists."""
        assert "python" in TEST_WRAPPERS
        wrapper = TEST_WRAPPERS["python"]
        assert "{code}" in wrapper
        assert "{test_input}" in wrapper
        assert "{expected_output}" in wrapper

    def test_javascript_wrapper_exists(self):
        """Test JavaScript test wrapper template exists."""
        assert "javascript" in TEST_WRAPPERS
        wrapper = TEST_WRAPPERS["javascript"]
        assert "{code}" in wrapper


class TestCodeSandbox:
    """Tests for CodeSandbox class."""

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        with patch("docker.from_env") as mock_from_env:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_from_env.return_value = mock_client
            yield mock_client

    def test_sandbox_initialization_disabled(self):
        """Test sandbox initializes as disabled when specified."""
        sandbox = CodeSandbox(enabled=False)
        assert sandbox.enabled is False

    def test_sandbox_default_timeout(self):
        """Test sandbox has default timeout."""
        sandbox = CodeSandbox(enabled=False)
        assert sandbox.timeout == CodeSandbox.DEFAULT_TIMEOUT

    def test_sandbox_custom_timeout(self):
        """Test sandbox accepts custom timeout."""
        sandbox = CodeSandbox(timeout=30, enabled=False)
        assert sandbox.timeout == 30

    @pytest.mark.asyncio
    async def test_execute_disabled_sandbox(self):
        """Test execute returns error when sandbox is disabled."""
        sandbox = CodeSandbox(enabled=False)
        result = await sandbox.execute_code("print('hello')", "python")

        assert result.success is False
        assert "not enabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self, mock_docker_client):
        """Test execute returns error for unsupported language."""
        sandbox = CodeSandbox(enabled=True)
        sandbox.docker_client = mock_docker_client
        result = await sandbox.execute_code("print('hello')", "rust")

        assert result.success is False
        assert "unsupported language" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_tests_disabled_sandbox(self):
        """Test run_tests returns errors when sandbox is disabled."""
        sandbox = CodeSandbox(enabled=False)
        test_cases = [
            {"input": "5", "expected": "10"},
            {"input": "3", "expected": "6"},
        ]
        results = await sandbox.run_tests(
            code="def solution(x): return x * 2",
            test_cases=test_cases,
            language="python",
        )

        assert len(results) == 2
        assert all(not r.passed for r in results)
        assert all("not enabled" in r.error.lower() for r in results)

    def test_create_test_wrapper_python(self):
        """Test Python test wrapper creation."""
        sandbox = CodeSandbox(enabled=False)
        code = "def solution(x): return x * 2"
        wrapper = sandbox._create_test_wrapper(
            code=code,
            test_input="5",
            expected_output="10",
            language="python",
        )

        assert code in wrapper
        assert "solution" in wrapper
        assert "json" in wrapper.lower()

    def test_create_test_wrapper_javascript(self):
        """Test JavaScript test wrapper creation."""
        sandbox = CodeSandbox(enabled=False)
        code = "function solution(x) { return x * 2; }"
        wrapper = sandbox._create_test_wrapper(
            code=code,
            test_input="5",
            expected_output="10",
            language="javascript",
        )

        assert code in wrapper
        assert "testInput" in wrapper

    def test_create_test_wrapper_json_input(self):
        """Test wrapper handles JSON input correctly."""
        sandbox = CodeSandbox(enabled=False)
        wrapper = sandbox._create_test_wrapper(
            code="def solution(x): return x",
            test_input="[1, 2, 3]",
            expected_output="[1, 2, 3]",
            language="python",
        )

        assert "[1, 2, 3]" in wrapper

    def test_create_test_wrapper_string_input(self):
        """Test wrapper handles string input correctly."""
        sandbox = CodeSandbox(enabled=False)
        wrapper = sandbox._create_test_wrapper(
            code="def solution(x): return x",
            test_input="hello",
            expected_output="hello",
            language="python",
        )

        assert "hello" in wrapper


class TestCodeSandboxSecurityLimits:
    """Tests for sandbox security limits."""

    def test_memory_limit_constant(self):
        """Test memory limit is defined."""
        assert CodeSandbox.MEMORY_LIMIT == "128m"

    def test_cpu_quota_constant(self):
        """Test CPU quota is defined."""
        assert CodeSandbox.CPU_QUOTA == 50000

    def test_max_pids_constant(self):
        """Test max PIDs limit is defined."""
        assert CodeSandbox.MAX_PIDS == 50

    def test_default_timeout_constant(self):
        """Test default timeout is defined."""
        assert CodeSandbox.DEFAULT_TIMEOUT == 10


class TestGetCodeSandbox:
    """Tests for get_code_sandbox singleton."""

    def test_returns_sandbox_instance(self):
        """Test get_code_sandbox returns CodeSandbox instance."""
        # Reset singleton for test
        import app.services.learning.code_sandbox as sandbox_module

        sandbox_module._sandbox_instance = None

        sandbox = get_code_sandbox()
        assert isinstance(sandbox, CodeSandbox)

    def test_returns_same_instance(self):
        """Test get_code_sandbox returns singleton."""
        sandbox1 = get_code_sandbox()
        sandbox2 = get_code_sandbox()
        assert sandbox1 is sandbox2


@pytest.mark.skipif(
    not pytest.importorskip("docker", reason="Docker not available"),
    reason="Docker not available",
)
class TestCodeSandboxIntegration:
    """Integration tests requiring Docker.

    These tests are skipped if Docker is not available.
    """

    @pytest.fixture
    def sandbox(self):
        """Create a real sandbox for integration tests."""
        sandbox = CodeSandbox(enabled=True, timeout=10)
        if not sandbox.enabled:
            pytest.skip("Docker not available")
        return sandbox

    @pytest.mark.asyncio
    async def test_execute_simple_python(self, sandbox):
        """Test executing simple Python code."""
        result = await sandbox.execute_code(
            code="print('Hello, World!')",
            language="python",
        )

        assert result.success is True
        assert "Hello, World!" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_python_with_error(self, sandbox):
        """Test executing Python code with syntax error."""
        result = await sandbox.execute_code(
            code="print('unclosed string",
            language="python",
        )

        assert result.success is False
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_run_python_tests_pass(self, sandbox):
        """Test running passing Python tests."""
        code = "def solution(x): return x * 2"
        test_cases = [
            {"input": "5", "expected": "10"},
            {"input": "3", "expected": "6"},
        ]

        results = await sandbox.run_tests(code, test_cases, "python")

        assert len(results) == 2
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_run_python_tests_fail(self, sandbox):
        """Test running failing Python tests."""
        code = "def solution(x): return x + 1"  # Wrong implementation
        test_cases = [
            {"input": "5", "expected": "10"},
        ]

        results = await sandbox.run_tests(code, test_cases, "python")

        assert len(results) == 1
        assert not results[0].passed
        assert results[0].actual == "6"
        assert results[0].expected == "10"
