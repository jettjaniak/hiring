"""
Task condition evaluation utilities

Provides safe expression evaluation for task completion and display conditions.
"""
from datetime import datetime, timedelta, date
import ast
from typing import Any, Optional


def safe_eval_condition(candidate: Any, expression: Optional[str]) -> bool:
    """
    Safely evaluate a condition expression against a candidate.

    Args:
        candidate: Candidate object with fields to evaluate
        expression: Python expression string (e.g., "work_permit_verified and background_check_date >= today()")
                   If None or empty, returns True (no condition)

    Returns:
        Boolean result of the evaluation. Returns True if no condition specified.
        On error, returns True (fail-open to avoid blocking valid operations)

    Examples:
        safe_eval_condition(candidate, "work_permit_verified")
        safe_eval_condition(candidate, "background_check_date >= days_ago(90)")
        safe_eval_condition(candidate, "requires_visa and visa_expiry > today()")
    """
    if not expression or not expression.strip():
        return True

    # Build context with candidate fields
    context = {}
    for field in dir(candidate):
        if not field.startswith('_') and not callable(getattr(candidate, field, None)):
            value = getattr(candidate, field, None)
            # Convert datetime objects to comparable dates
            if isinstance(value, datetime):
                value = value.date()
            context[field] = value

    # Add safe helper functions
    safe_builtins = {
        'True': True,
        'False': False,
        'None': None,
        # Date helpers
        'today': lambda: date.today(),
        'days_ago': lambda n: date.today() - timedelta(days=int(n)),
        'days_from_now': lambda n: date.today() + timedelta(days=int(n)),
    }

    try:
        # Parse and validate AST
        tree = ast.parse(expression, mode='eval')

        # Whitelist allowed node types
        allowed_nodes = (
            ast.Expression, ast.Compare, ast.BoolOp, ast.UnaryOp,
            ast.Name, ast.Constant, ast.Load, ast.Num, ast.Str,
            ast.And, ast.Or, ast.Not,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.Call,  # Allow function calls
            ast.In, ast.NotIn,
            ast.Is, ast.IsNot,  # Allow 'is' and 'is not' for None checks
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Unsafe operation: {type(node).__name__}")

        # Additional safety: only allow whitelisted function names
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in safe_builtins:
                        raise ValueError(f"Function not allowed: {node.func.id}")

        # Evaluate
        code = compile(tree, '<string>', 'eval')
        result = eval(code, {"__builtins__": {}}, {**context, **safe_builtins})
        return bool(result)

    except Exception as e:
        # Log the error for debugging
        print(f"Error evaluating condition '{expression}': {e}")
        return True  # Fail-open: allow operation if condition evaluation fails


def validate_condition_expression(expression: Optional[str]) -> tuple[bool, str]:
    """
    Validate a condition expression without evaluating it.

    Args:
        expression: Python expression string to validate

    Returns:
        Tuple of (is_valid, message)
    """
    if not expression or not expression.strip():
        return True, "No condition (always true)"

    try:
        # Parse to check syntax
        tree = ast.parse(expression, mode='eval')

        # Whitelist allowed node types
        allowed_nodes = (
            ast.Expression, ast.Compare, ast.BoolOp, ast.UnaryOp,
            ast.Name, ast.Constant, ast.Load, ast.Num, ast.Str,
            ast.And, ast.Or, ast.Not,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.Call,
            ast.In, ast.NotIn,
            ast.Is, ast.IsNot,  # Allow 'is' and 'is not' for None checks
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return False, f"Unsafe operation not allowed: {type(node).__name__}"

        # Check function names
        allowed_functions = {'today', 'days_ago', 'days_from_now'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in allowed_functions:
                        return False, f"Function not allowed: {node.func.id}(). Allowed functions: {', '.join(allowed_functions)}"

        return True, "Valid expression"

    except SyntaxError as e:
        return False, f"Syntax error: {e.msg}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
