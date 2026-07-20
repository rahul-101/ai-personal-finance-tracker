import unittest
from unittest.mock import Mock, patch

from models import MonthlyBudget
from routes.budgets import get_budget_for_month, get_current_budget, save_current_budget


class BudgetRouteTests(unittest.TestCase):
    def test_current_budget_calculates_confirmed_monthly_spending(self):
        budget_collection = Mock()
        budget_collection.find_one.return_value = {
            "monthly_limit": 10000,
            "category_limits": {"Food": 3000},
        }
        transactions_collection = Mock()
        transactions_collection.find.return_value = [
            {"amount": 1200, "category": "Food", "transaction_type": "debit", "status": "confirmed"},
            {"amount": 500, "category": "Food", "transaction_type": "debit", "status": "review_required"},
            {"amount": 900, "category": "Income", "transaction_type": "credit", "status": "confirmed"},
        ]

        with patch("routes.budgets.budgets_collection", budget_collection), \
             patch("routes.budgets.transactions_collection", transactions_collection), \
             patch("routes.budgets.current_month_key", return_value="2026-07"):
            result = get_current_budget()

        self.assertEqual(result["overall"]["spent"], 1200)
        self.assertEqual(result["overall"]["remaining"], 8800)
        self.assertEqual(result["categories"][0]["percent_used"], 40.0)

    def test_save_budget_upserts_the_single_user_configuration(self):
        budget_collection = Mock()
        budget_collection.find_one.return_value = {"monthly_limit": 5000, "category_limits": {"Shopping": 2000}}
        transactions_collection = Mock()
        transactions_collection.find.return_value = []

        with patch("routes.budgets.budgets_collection", budget_collection), \
             patch("routes.budgets.transactions_collection", transactions_collection), \
             patch("routes.budgets.current_month_key", return_value="2026-07"):
            result = save_current_budget(MonthlyBudget(monthly_limit=5000, category_limits={"Shopping": 2000}))

        self.assertEqual(result["overall"]["limit"], 5000)
        self.assertEqual(budget_collection.update_one.call_args.args[0]["scope"], "monthly")
        self.assertRegex(budget_collection.update_one.call_args.args[0]["month"], r"^\d{4}-\d{2}$")
        self.assertTrue(budget_collection.update_one.call_args.kwargs["upsert"])

    def test_loads_a_historical_month_budget(self):
        budget_collection = Mock()
        budget_collection.find_one.return_value = {"monthly_limit": 4000, "category_limits": {"Food": 1500}}
        transactions_collection = Mock()
        transactions_collection.find.return_value = [{"amount": 800, "category": "Food", "transaction_type": "expense", "status": "confirmed"}]

        with patch("routes.budgets.budgets_collection", budget_collection), \
             patch("routes.budgets.transactions_collection", transactions_collection):
            result = get_budget_for_month("2026-06")

        self.assertEqual(result["month"], "2026-06")
        self.assertEqual(result["overall"]["remaining"], 3200)
        self.assertEqual(budget_collection.find_one.call_args.args[0], {"scope": "monthly", "month": "2026-06"})
