import pytest
from app.domain.condition_evaluator import ConditionEvaluator


class TestConditionEvaluator:
    # --- operator > ---
    def test_greater_than_true(self):
        assert ConditionEvaluator.evaluate(35, ">", 30) is True

    def test_greater_than_false(self):
        assert ConditionEvaluator.evaluate(25, ">", 30) is False

    def test_greater_than_equal_is_false(self):
        assert ConditionEvaluator.evaluate(30, ">", 30) is False

    # --- operator < ---
    def test_less_than_true(self):
        assert ConditionEvaluator.evaluate(20, "<", 30) is True

    def test_less_than_false(self):
        assert ConditionEvaluator.evaluate(35, "<", 30) is False

    # --- operator >= ---
    def test_gte_equal(self):
        assert ConditionEvaluator.evaluate(30, ">=", 30) is True

    def test_gte_above(self):
        assert ConditionEvaluator.evaluate(31, ">=", 30) is True

    def test_gte_below(self):
        assert ConditionEvaluator.evaluate(29, ">=", 30) is False

    # --- operator <= ---
    def test_lte_equal(self):
        assert ConditionEvaluator.evaluate(30, "<=", 30) is True

    def test_lte_below(self):
        assert ConditionEvaluator.evaluate(29, "<=", 30) is True

    def test_lte_above(self):
        assert ConditionEvaluator.evaluate(31, "<=", 30) is False

    # --- operator == ---
    def test_eq_true(self):
        assert ConditionEvaluator.evaluate(30, "==", 30) is True

    def test_eq_false(self):
        assert ConditionEvaluator.evaluate(29, "==", 30) is False

    # --- None value ---
    def test_none_value_always_false(self):
        for op in [">", "<", ">=", "<=", "=="]:
            assert ConditionEvaluator.evaluate(None, op, 30) is False

    # --- Invalid operator ---
    def test_invalid_operator_raises(self):
        with pytest.raises(ValueError, match="Unsupported operator"):
            ConditionEvaluator.evaluate(30, "!=", 30)

    # --- Boolean (motion_detected) ---
    def test_boolean_eq_true(self):
        assert ConditionEvaluator.evaluate(True, "==", 1) is True

    def test_boolean_eq_false(self):
        assert ConditionEvaluator.evaluate(False, "==", 1) is False
