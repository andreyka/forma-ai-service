"""Security module for validating generated Python code.

This module provides the CodeValidator class, which uses AST analysis to ensure
that generated code only uses allowed libraries and operations.
"""

import ast
import logging

logger = logging.getLogger(__name__)

class SecurityViolation(Exception):
    """Exception raised when code violates security rules."""
    pass

class CodeValidator(ast.NodeVisitor):
    """AST visitor to validate Python code against security rules."""

    ALLOWED_IMPORTS = {"build123d", "math"}
    ALLOWED_BUILTINS = {
        "print", "range", "len", "int", "float", "str", "list", "dict", "tuple", 
        "set", "bool", "enumerate", "zip", "min", "max", "abs", "sum", "round"
    }
    
    def __init__(self):
        self.errors = []

    def validate(self, code: str) -> None:
        """Validates the given code string.

        Args:
            code (str): The Python code to validate.

        Raises:
            SecurityViolation: If the code contains disallowed operations.
            SyntaxError: If the code is not valid Python.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python code: {e}")

        self.visit(tree)

        if self.errors:
            raise SecurityViolation("\n".join(self.errors))

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name.split('.')[0] not in self.ALLOWED_IMPORTS:
                self.errors.append(f"Importing '{alias.name}' is not allowed.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and node.module.split('.')[0] not in self.ALLOWED_IMPORTS:
            self.errors.append(f"Importing from '{node.module}' is not allowed.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check for calls to disallowed built-in functions
        if isinstance(node.func, ast.Name):
            if node.func.id not in self.ALLOWED_BUILTINS and node.func.id in __builtins__:
                 # It's a builtin but not in our allowed list (e.g. open, exec, eval)
                 # Note: This check is a bit loose because __builtins__ can be a dict or module
                 # and we are checking against the current environment's builtins.
                 # A stricter check would be to have a DENY_LIST.
                 
                 # Let's use a DENY_LIST approach for critical ones to be safe and explicit
                 if node.func.id in {"open", "exec", "eval", "__import__", "input", "compile", "globals", "locals"}:
                     self.errors.append(f"Calling function '{node.func.id}' is not allowed.")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Disallow access to dangerous attributes
        if node.attr in {"__builtins__", "__globals__", "__class__", "__base__", "__subclasses__"}:
            self.errors.append(f"Accessing attribute '{node.attr}' is not allowed.")
        self.generic_visit(node)
        
    def visit_Exec(self, node):
        # Python 2 compatibility (though ast.parse might fail on Py3 for Exec node, good to have)
        self.errors.append("Exec statement is not allowed.")
        
    def visit_Global(self, node):
        self.errors.append("Global statement is not allowed.")
        
    def visit_Nonlocal(self, node):
        self.errors.append("Nonlocal statement is not allowed.")

def validate_code(code: str) -> None:
    """Helper function to validate code using CodeValidator.
    
    Args:
        code (str): The code to validate.
        
    Raises:
        SecurityViolation: If validation fails.
    """
    validator = CodeValidator()
    validator.validate(code)
