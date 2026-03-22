"""Unit tests for all tools in the tools/ package."""

import pytest
from tools.existing_tools import calculator
from tools.unit_converter import convert_units
from tools.datetime_tool import datetime_info
from tools.python_repl import python_execute, _check_imports
from tools.webpage_reader import _is_safe_url


# --- Calculator ---

class TestCalculator:
    def test_add(self):
        result = calculator.invoke({"first_num": 2, "second_num": 3, "operation": "add"})
        assert result == {"result": 5}

    def test_sub(self):
        result = calculator.invoke({"first_num": 10, "second_num": 4, "operation": "sub"})
        assert result == {"result": 6}

    def test_mul(self):
        result = calculator.invoke({"first_num": 3, "second_num": 7, "operation": "mul"})
        assert result == {"result": 21}

    def test_div(self):
        result = calculator.invoke({"first_num": 10, "second_num": 2, "operation": "div"})
        assert result == {"result": 5.0}

    def test_div_by_zero(self):
        result = calculator.invoke({"first_num": 5, "second_num": 0, "operation": "div"})
        assert "error" in result

    def test_unsupported_op(self):
        result = calculator.invoke({"first_num": 1, "second_num": 1, "operation": "pow"})
        assert "error" in result


# --- Unit Converter ---

class TestUnitConverter:
    def test_km_to_miles(self):
        result = convert_units.invoke({"value": 100, "from_unit": "km", "to_unit": "miles"})
        assert "62.14" in result

    def test_kg_to_lb(self):
        result = convert_units.invoke({"value": 1, "from_unit": "kg", "to_unit": "lb"})
        assert "2.205" in result

    def test_invalid_units(self):
        result = convert_units.invoke({"value": 1, "from_unit": "kg", "to_unit": "km"})
        assert "Error" in result


# --- DateTime ---

class TestDatetime:
    def test_now(self):
        result = datetime_info.invoke({"action": "now", "timezone": "UTC"})
        assert "Current date/time" in result

    def test_diff(self):
        result = datetime_info.invoke({"action": "diff", "date1": "2026-01-01", "date2": "2026-01-10"})
        assert "9 days" in result

    def test_day_of_week(self):
        result = datetime_info.invoke({"action": "day_of_week", "date1": "2026-03-22"})
        assert "Sunday" in result

    def test_add_days(self):
        result = datetime_info.invoke({"action": "add_days", "date1": "2026-01-01", "date2": "10"})
        assert "2026-01-11" in result

    def test_invalid_action(self):
        result = datetime_info.invoke({"action": "xyz"})
        assert "Unknown action" in result


# --- Python REPL ---

class TestPythonRepl:
    def test_simple_print(self):
        result = python_execute.invoke({"code": "print(2 + 2)"})
        assert "4" in result

    def test_blocked_import_os(self):
        result = python_execute.invoke({"code": "import os; print(os.getcwd())"})
        assert "not allowed" in result

    def test_blocked_import_subprocess(self):
        result = python_execute.invoke({"code": "import subprocess"})
        assert "not allowed" in result

    def test_timeout(self):
        result = python_execute.invoke({"code": "import time; time.sleep(10)"})
        assert "timed out" in result

    def test_import_check_function(self):
        assert _check_imports("import os") == "os"
        assert _check_imports("from subprocess import run") == "subprocess"
        assert _check_imports("import math") is None


# --- SSRF Prevention ---

class TestSSRF:
    def test_blocks_localhost(self):
        assert _is_safe_url("http://localhost/secret") is False

    def test_blocks_private_ip(self):
        assert _is_safe_url("http://192.168.1.1/admin") is False
        assert _is_safe_url("http://10.0.0.1/") is False
        assert _is_safe_url("http://127.0.0.1/") is False

    def test_blocks_non_http(self):
        assert _is_safe_url("file:///etc/passwd") is False
        assert _is_safe_url("ftp://example.com") is False

    def test_allows_public_urls(self):
        assert _is_safe_url("https://en.wikipedia.org/wiki/Python") is True
        assert _is_safe_url("https://example.com") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
