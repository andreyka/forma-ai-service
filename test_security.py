import unittest
from tools.security import validate_code, SecurityViolation

class TestSecurityValidator(unittest.TestCase):
    def test_valid_code(self):
        code = """
import build123d
from build123d import *
import math

def create_cube():
    return Box(10, 10, 10)

result = create_cube()
"""
        try:
            validate_code(code)
        except SecurityViolation:
            self.fail("validate_code raised SecurityViolation unexpectedly!")

    def test_invalid_import(self):
        code = "import os"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_import_from(self):
        code = "from subprocess import run"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_builtin_call(self):
        code = "open('/etc/passwd')"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_exec(self):
        code = "exec('print(1)')"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_eval(self):
        code = "eval('1+1')"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_attribute_access(self):
        code = "print([].__class__.__base__)"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

    def test_invalid_dunder_import(self):
        code = "__import__('os').system('ls')"
        with self.assertRaises(SecurityViolation):
            validate_code(code)

if __name__ == '__main__':
    unittest.main()
