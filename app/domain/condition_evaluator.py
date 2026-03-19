
class ConditionEvaluator:
    OPERATORS = {
        ">": lambda a, b: a is not None and a > b,
        "<": lambda a, b: a is not None and a < b,
        ">=": lambda a, b: a is not None and a >= b,
        "<=": lambda a, b: a is not None and a <= b,
        "==": lambda a, b: a is not None and a == b,
    }

    @classmethod
    def evaluate(cls, current_value, operator: str, threshold_value: float) -> bool:
        if operator not in cls.OPERATORS:
            raise ValueError("Unsupported operator")
        return cls.OPERATORS[operator](current_value, threshold_value)
