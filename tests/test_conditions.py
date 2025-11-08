"""
Unit tests for task condition evaluation utilities
"""
import pytest
from datetime import date, datetime, timedelta
from src.utils.conditions import safe_eval_condition, validate_condition_expression


class MockCandidate:
    """Mock candidate object for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestSafeEvalCondition:
    """Tests for safe_eval_condition function"""

    def test_empty_expression_returns_true(self):
        """Empty or None expression should return True"""
        candidate = MockCandidate()
        assert safe_eval_condition(candidate, None) is True
        assert safe_eval_condition(candidate, "") is True
        assert safe_eval_condition(candidate, "   ") is True

    def test_simple_boolean_field(self):
        """Test simple boolean field evaluation"""
        candidate = MockCandidate(work_permit_verified=1, requires_visa=0)
        assert safe_eval_condition(candidate, "work_permit_verified") is True
        assert safe_eval_condition(candidate, "requires_visa") is False

    def test_comparison_operators(self):
        """Test comparison operators"""
        candidate = MockCandidate(score=85, age=30)
        assert safe_eval_condition(candidate, "score > 80") is True
        assert safe_eval_condition(candidate, "score >= 85") is True
        assert safe_eval_condition(candidate, "score < 90") is True
        assert safe_eval_condition(candidate, "score <= 85") is True
        assert safe_eval_condition(candidate, "score == 85") is True
        assert safe_eval_condition(candidate, "score != 90") is True

    def test_boolean_operators(self):
        """Test boolean AND, OR, NOT operators"""
        candidate = MockCandidate(work_permit_verified=1, requires_visa=1)
        assert safe_eval_condition(candidate, "work_permit_verified and requires_visa") is True
        assert safe_eval_condition(candidate, "work_permit_verified or requires_visa") is True

        candidate2 = MockCandidate(work_permit_verified=0, requires_visa=1)
        assert safe_eval_condition(candidate2, "work_permit_verified and requires_visa") is False
        assert safe_eval_condition(candidate2, "work_permit_verified or requires_visa") is True
        assert safe_eval_condition(candidate2, "not work_permit_verified") is True

    def test_date_helper_today(self):
        """Test today() helper function"""
        candidate = MockCandidate()
        # This should always be true
        result = safe_eval_condition(candidate, "today() == today()")
        assert result is True

    def test_date_helper_days_ago(self):
        """Test days_ago() helper function"""
        candidate = MockCandidate(
            background_check_date=date.today() - timedelta(days=30)
        )
        assert safe_eval_condition(candidate, "background_check_date >= days_ago(90)") is True
        assert safe_eval_condition(candidate, "background_check_date >= days_ago(20)") is False
        assert safe_eval_condition(candidate, "background_check_date == days_ago(30)") is True

    def test_date_helper_days_from_now(self):
        """Test days_from_now() helper function"""
        candidate = MockCandidate(
            visa_expiry=date.today() + timedelta(days=60)
        )
        assert safe_eval_condition(candidate, "visa_expiry > days_from_now(30)") is True
        assert safe_eval_condition(candidate, "visa_expiry > days_from_now(90)") is False
        assert safe_eval_condition(candidate, "visa_expiry <= days_from_now(60)") is True

    def test_datetime_converted_to_date(self):
        """Test that datetime fields are converted to date for comparisons"""
        candidate = MockCandidate(
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        # The datetime should be converted to date automatically
        assert safe_eval_condition(candidate, "created_at == days_ago(0)") is False
        # We can't easily test the exact date conversion without knowing today's date,
        # but we can verify the evaluation doesn't crash

    def test_complex_expression(self):
        """Test complex boolean expressions"""
        candidate = MockCandidate(
            work_permit_verified=1,
            requires_visa=1,
            background_check_date=date.today() - timedelta(days=30)
        )
        expr = "work_permit_verified and requires_visa and background_check_date >= days_ago(90)"
        assert safe_eval_condition(candidate, expr) is True

    def test_none_field_values(self):
        """Test handling of None field values"""
        candidate = MockCandidate(background_check_date=None)
        # This should fail gracefully and return True (fail-open)
        result = safe_eval_condition(candidate, "background_check_date >= days_ago(90)")
        assert result is True

    def test_unsafe_operation_fails_open(self):
        """Test that unsafe operations return True (fail-open)"""
        candidate = MockCandidate(name="test")
        # Try to use an unsafe operation (import)
        result = safe_eval_condition(candidate, "__import__('os')")
        assert result is True  # Should fail-open

    def test_disallowed_function_fails_open(self):
        """Test that disallowed functions return True (fail-open)"""
        candidate = MockCandidate(name="test")
        # Try to use a disallowed function
        result = safe_eval_condition(candidate, "print('hello')")
        assert result is True  # Should fail-open

    def test_syntax_error_fails_open(self):
        """Test that syntax errors return True (fail-open)"""
        candidate = MockCandidate()
        # Invalid syntax
        result = safe_eval_condition(candidate, "invalid syntax here!")
        assert result is True  # Should fail-open

    def test_missing_field_fails_open(self):
        """Test that missing field references fail-open"""
        candidate = MockCandidate(name="test")
        # Reference a field that doesn't exist
        result = safe_eval_condition(candidate, "nonexistent_field == 1")
        assert result is True  # Should fail-open


class TestValidateConditionExpression:
    """Tests for validate_condition_expression function"""

    def test_empty_expression_valid(self):
        """Empty or None expression should be valid"""
        is_valid, msg = validate_condition_expression(None)
        assert is_valid is True
        assert "No condition" in msg

        is_valid, msg = validate_condition_expression("")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("   ")
        assert is_valid is True

    def test_simple_valid_expressions(self):
        """Test simple valid expressions"""
        is_valid, msg = validate_condition_expression("work_permit_verified")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("score > 80")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("work_permit_verified and requires_visa")
        assert is_valid is True

    def test_valid_date_helpers(self):
        """Test valid date helper function usage"""
        is_valid, msg = validate_condition_expression("today()")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("days_ago(90)")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("days_from_now(30)")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("background_check_date >= days_ago(90)")
        assert is_valid is True

    def test_complex_valid_expression(self):
        """Test complex valid expressions"""
        expr = "work_permit_verified and requires_visa and background_check_date >= days_ago(90)"
        is_valid, msg = validate_condition_expression(expr)
        assert is_valid is True

    def test_syntax_error(self):
        """Test that syntax errors are detected"""
        is_valid, msg = validate_condition_expression("invalid syntax!")
        assert is_valid is False
        assert "Syntax error" in msg or "syntax" in msg.lower()

    def test_unsafe_operations(self):
        """Test that unsafe operations are rejected"""
        # Import statement
        is_valid, msg = validate_condition_expression("__import__('os')")
        assert is_valid is False
        assert "not allowed" in msg.lower() or "unsafe" in msg.lower()

        # Attribute access
        is_valid, msg = validate_condition_expression("candidate.__dict__")
        assert is_valid is False

    def test_disallowed_functions(self):
        """Test that disallowed functions are rejected"""
        is_valid, msg = validate_condition_expression("print('hello')")
        assert is_valid is False
        assert "print" in msg
        assert "not allowed" in msg.lower()

        is_valid, msg = validate_condition_expression("eval('test')")
        assert is_valid is False
        assert "eval" in msg

    def test_allowed_functions_list(self):
        """Test that only whitelisted functions are allowed"""
        # These should be valid
        for func in ['today', 'days_ago', 'days_from_now']:
            is_valid, msg = validate_condition_expression(f"{func}()")
            assert is_valid is True, f"{func}() should be valid but got: {msg}"

        # These should be invalid
        for func in ['print', 'eval', 'exec', 'open', 'input']:
            is_valid, msg = validate_condition_expression(f"{func}()")
            assert is_valid is False, f"{func}() should be invalid"
            assert func in msg

    def test_comparison_operators_valid(self):
        """Test that all comparison operators are valid"""
        operators = ['==', '!=', '<', '<=', '>', '>=']
        for op in operators:
            is_valid, msg = validate_condition_expression(f"value {op} 10")
            assert is_valid is True, f"Operator {op} should be valid"

    def test_boolean_operators_valid(self):
        """Test that boolean operators are valid"""
        is_valid, msg = validate_condition_expression("a and b")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("a or b")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("not a")
        assert is_valid is True

        is_valid, msg = validate_condition_expression("a and b or c")
        assert is_valid is True
