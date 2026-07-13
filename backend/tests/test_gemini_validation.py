import unittest

from services.gemini_ai import fallback_ai_result, validate_ai_result


RULE_BASED_RESULT = {
    "is_transaction": True,
    "date": "2026-07-13",
    "merchant": "Swiggy",
    "amount": 849.0,
    "category": "Food",
    "source": "email",
    "transaction_type": "debit",
}


class GeminiValidationTests(unittest.TestCase):
    def test_invalid_ai_result_uses_rule_based_fallback(self):
        result = validate_ai_result(
            candidate={
                "category": "Invalid category",
                "confidence": 5,
            },
            fallback=fallback_ai_result(RULE_BASED_RESULT),
        )

        self.assertEqual(result["merchant"], "Swiggy")
        self.assertEqual(result["category"], "Food")
        self.assertEqual(result["confidence"], 0.70)
        self.assertIn("invalid finance data", result["reason"])
