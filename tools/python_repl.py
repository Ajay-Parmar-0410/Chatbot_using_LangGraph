"""Sandboxed Python code execution tool."""

import subprocess
import re

from langchain_core.tools import tool

# Dangerous imports to block
_BLOCKED_IMPORTS = {
    "os", "subprocess", "shutil", "sys", "pathlib",
    "socket", "http", "urllib", "requests", "httpx",
    "ctypes", "signal", "multiprocessing", "threading",
}

_IMPORT_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:import|from)\s+(\w+)', re.MULTILINE
)

MAX_OUTPUT_LENGTH = 3000
TIMEOUT_SECONDS = 5


def _check_imports(code: str) -> "Optional[str]":
    """Return the first blocked import found, or None if all safe."""
    for match in _IMPORT_PATTERN.finditer(code):
        module = match.group(1)
        if module in _BLOCKED_IMPORTS:
            return module
    return None


@tool
def python_execute(code: str) -> str:
    """Execute Python code and return the output.
    Use for calculations, data processing, or logic tasks.
    Print results using print() to see output."""
    # Check for dangerous imports
    blocked = _check_imports(code)
    if blocked:
        return f"Error: Import '{blocked}' is not allowed for security reasons."

    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=None,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr

        if not output:
            output = "(No output)"

        # Truncate
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n\n[Output truncated...]"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (5 second limit)."
    except Exception as e:
        return f"Error executing code: {str(e)}"
