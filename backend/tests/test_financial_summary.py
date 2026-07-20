import unittest
from unittest.mock import Mock, patch

from models import Transaction
from routes.dashboard import dashboard_summary


class FinancialSummaryTests(unittest.TestCase):
    def test_dashboard_separates_income_expenses_investments_transfers_and_refunds(self):
        transactions = Mock()
        transactions.find.return_value = [
            {"amount": 5000, "merchant": "Employer", "category": "Income", "transaction_type": "income", "status": "confirmed", "date": "2026-07-01", "source": "manual"},
            {"amount": 1200, "merchant": "Store", "category": "Shopping", "transaction_type": "expense", "status": "confirmed", "date": "2026-07-02", "source": "manual"},
            {"amount": 600, "merchant": "Fund", "category": "Investment", "transaction_type": "investment", "status": "confirmed", "date": "2026-07-03", "source": "manual"},
            {"amount": 150, "merchant": "Store", "category": "Refund", "transaction_type": "refund", "status": "confirmed", "date": "2026-07-04", "source": "email"},
            {"amount": 1000, "merchant": "Self", "category": "Transfer", "transaction_type": "transfer", "status": "confirmed", "date": "2026-07-05", "source": "manual"},
        ]
        gmail_logs = Mock()
        gmail_logs.count_documents.return_value = 0
        bills = Mock()
        bills.count_documents.return_value = 0

        with patch("routes.dashboard.transactions_collection", transactions), \
             patch("routes.dashboard.gmail_logs_collection", gmail_logs), \
             patch("routes.dashboard.bills_collection", bills):
            result = dashboard_summary()["summary"]

        self.assertEqual(result["total_income"], 5000)
        self.assertEqual(result["total_expenses"], 1200)
        self.assertEqual(result["total_investments"], 600)
        self.assertEqual(result["total_refunds"], 150)
        self.assertEqual(result["total_transfers"], 1000)
        self.assertEqual(result["net_cash_flow"], 3350)
        self.assertEqual(result["category_summary"], {"Shopping": 1200})

    def test_manual_transactions_accept_the_new_financial_types(self):
        transaction = Transaction(
            date="2026-07-20", merchant="Index Fund", amount=1000, category="Investment",
            source="manual", transaction_type="investment",
        )

        self.assertEqual(transaction.transaction_type, "investment")

    def test_dashboard_can_filter_the_summary_to_one_month(self):
        transactions = Mock()
        transactions.find.return_value = [
            {"amount": 100, "merchant": "July", "category": "Food", "transaction_type": "expense", "status": "confirmed", "date": "2026-07-01", "source": "manual"},
            {"amount": 200, "merchant": "June", "category": "Food", "transaction_type": "expense", "status": "confirmed", "date": "2026-06-01", "source": "manual"},
        ]
        gmail_logs = Mock()
        gmail_logs.count_documents.return_value = 0
        bills = Mock()
        bills.count_documents.return_value = 0

        with patch("routes.dashboard.transactions_collection", transactions), \
             patch("routes.dashboard.gmail_logs_collection", gmail_logs), \
             patch("routes.dashboard.bills_collection", bills):
            result = dashboard_summary("2026-07")["summary"]

        self.assertEqual(result["selected_month"], "2026-07")
        self.assertEqual(result["total_expenses"], 100)
        self.assertEqual(result["total_transactions"], 1)
