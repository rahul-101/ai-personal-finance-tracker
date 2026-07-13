import unittest

from pydantic import ValidationError

from models import GeminiEmailAnalysis, Transaction, TransactionReviewDecision


class TransactionModelTests(unittest.TestCase):
    def test_valid_manual_transaction_is_normalized(self):
        transaction = Transaction(
            date="2026-07-13",
            merchant="  Grocery Store  ",
            amount=250.50,
            category="  Groceries ",
            source="manual",
            notes="  Weekly shopping  ",
        )

        self.assertEqual(transaction.merchant, "Grocery Store")
        self.assertEqual(transaction.category, "Groceries")
        self.assertEqual(transaction.notes, "Weekly shopping")
        self.assertEqual(transaction.transaction_type, "debit")
        self.assertEqual(transaction.status, "confirmed")

    def test_transaction_rejects_invalid_financial_input(self):
        with self.assertRaises(ValidationError):
            Transaction(
                date="not-a-date",
                merchant=" ",
                amount=0,
                category="",
                source="unknown",
            )


class GeminiEmailAnalysisTests(unittest.TestCase):
    def test_accepts_valid_ai_analysis(self):
        analysis = GeminiEmailAnalysis.model_validate(
            {
                "is_transaction": True,
                "date": "2026-07-13",
                "merchant": "  Swiggy  ",
                "amount": 849,
                "category": "Food",
                "source": "email",
                "transaction_type": "debit",
                "confidence": 0.92,
                "payment_mode": "upi",
                "reason": "Debit alert contains merchant and amount.",
            }
        )

        self.assertEqual(analysis.merchant, "Swiggy")
        self.assertEqual(analysis.confidence, 0.92)

    def test_rejects_invalid_ai_finance_data(self):
        with self.assertRaises(ValidationError):
            GeminiEmailAnalysis.model_validate(
                {
                    "is_transaction": True,
                    "merchant": "Swiggy",
                    "amount": -849,
                    "category": "Cryptocurrency",
                    "source": "manual",
                    "confidence": 2,
                    "unexpected_provider_field": "not allowed",
                }
            )


class TransactionReviewDecisionTests(unittest.TestCase):
    def test_approval_can_include_a_corrected_amount(self):
        decision = TransactionReviewDecision(
            decision="approve",
            amount=799,
            review_note="Corrected OCR total",
        )

        self.assertEqual(decision.amount, 799)
        self.assertEqual(decision.review_note, "Corrected OCR total")

    def test_rejects_invalid_review_data(self):
        with self.assertRaises(ValidationError):
            TransactionReviewDecision(decision="approve", amount=0)
