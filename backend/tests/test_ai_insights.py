import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from routes.ai_settings import generate_finance_insights, generate_weekly_digest, get_finance_insight_history
from services.ai_client import AIProviderError


class AIInsightsRouteTests(unittest.TestCase):
    def test_returns_validated_provider_insights_from_aggregate_data(self):
        dashboard_result = {
            "status": "success",
            "summary": {
                "total_spend": 1200,
                "total_credit": 2000,
                "net_balance": 800,
                "total_transactions": 4,
                "review_required_count": 1,
                "review_log_count": 0,
                "bills_due_count": 2,
                "category_summary": {"Food": 600},
                "top_merchants": [{"merchant": "Cafe", "amount": 300}],
                "monthly_trend": [{"month": "2026-07", "amount": 1200}],
            },
        }
        provider_response = (
            '{"headline":"Keep an eye on food spending",'
            '"insights":["Review the pending transaction", "Plan for upcoming bills"],'
            '"disclaimer":"Educational information, not financial advice."}'
        )

        with patch("routes.ai_settings.is_ai_configured", return_value=True), \
             patch("routes.ai_settings.get_ai_configuration", return_value=SimpleNamespace(provider="openai", model="test-model")), \
             patch("routes.ai_settings.dashboard_summary", return_value=dashboard_result), \
             patch("routes.ai_settings.build_budget_response", return_value={"month": "2026-07", "overall": {"limit": 3000, "spent": 2500, "remaining": 500, "percent_used": 83.3}, "categories": []}), \
             patch("routes.ai_settings.get_profile_ai_preferences", return_value={"currency": "INR", "savings_goal": 10000, "priorities": ["Save more"]}), \
             patch("routes.ai_settings.generate_text", return_value=provider_response) as generate_text, \
             patch("routes.ai_settings.ai_insights_collection.insert_one") as insert_one:
            result = generate_finance_insights()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["insight"]["headline"], "Keep an eye on food spending")
        self.assertEqual(len(result["insight"]["insights"]), 2)
        self.assertIn("aggregate financial data", generate_text.call_args.args[0])
        self.assertIn('"budget"', generate_text.call_args.args[0])
        self.assertIn('"profile_preferences"', generate_text.call_args.args[0])
        self.assertEqual(insert_one.call_args.args[0]["provider"], "openai")

    def test_rejects_non_json_provider_responses(self):
        dashboard_result = {"status": "success", "summary": {
            "total_spend": 0, "total_credit": 0, "net_balance": 0, "total_transactions": 0,
            "review_required_count": 0, "review_log_count": 0, "bills_due_count": 0,
            "category_summary": {}, "top_merchants": [], "monthly_trend": [],
        }}

        with patch("routes.ai_settings.is_ai_configured", return_value=True), \
             patch("routes.ai_settings.get_ai_configuration", return_value=SimpleNamespace(provider="gemini", model="test-model")), \
             patch("routes.ai_settings.dashboard_summary", return_value=dashboard_result), \
             patch("routes.ai_settings.build_budget_response", return_value={"month": "2026-07", "overall": None, "categories": []}), \
             patch("routes.ai_settings.get_profile_ai_preferences", return_value={}), \
             patch("routes.ai_settings.generate_text", return_value="not json"):
            with self.assertRaises(Exception) as context:
                generate_finance_insights()

        self.assertEqual(context.exception.status_code, 503)

    def test_accepts_json_wrapped_in_a_markdown_code_fence(self):
        dashboard_result = {"status": "success", "summary": {
            "total_spend": 0, "total_credit": 0, "net_balance": 0, "total_transactions": 0,
            "review_required_count": 0, "review_log_count": 0, "bills_due_count": 0,
            "category_summary": {}, "top_merchants": [], "monthly_trend": [],
        }}
        provider_response = (
            "```json\n"
            '{"headline":"Overview","insights":["Add transactions to begin."],'
            '"disclaimer":"Educational information only."}\n'
            "```"
        )

        with patch("routes.ai_settings.is_ai_configured", return_value=True), \
             patch("routes.ai_settings.get_ai_configuration", return_value=SimpleNamespace(provider="gemini", model="test-model")), \
             patch("routes.ai_settings.dashboard_summary", return_value=dashboard_result), \
             patch("routes.ai_settings.build_budget_response", return_value={"month": "2026-07", "overall": None, "categories": []}), \
             patch("routes.ai_settings.get_profile_ai_preferences", return_value={}), \
             patch("routes.ai_settings.generate_text", return_value=provider_response), \
             patch("routes.ai_settings.ai_insights_collection.insert_one"):
            result = generate_finance_insights()

        self.assertEqual(result["insight"]["headline"], "Overview")

    def test_returns_recent_saved_insights(self):
        collection = Mock()
        collection.find.return_value.sort.return_value.limit.return_value = [{
            "_id": "insight-1",
            "headline": "Overview",
            "insights": ["Review spending."],
            "disclaimer": "Educational only.",
            "provider": "gemini",
            "model": "gemini-test",
            "created_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        }]

        with patch("routes.ai_settings.ai_insights_collection", collection):
            result = get_finance_insight_history()

        self.assertEqual(result["insights"][0]["_id"], "insight-1")
        self.assertEqual(result["insights"][0]["headline"], "Overview")

    def test_generates_a_weekly_digest_for_a_seven_day_range(self):
        dashboard_result = {"status": "success", "summary": {
            "total_spend": 900, "total_credit": 1500, "net_balance": 600,
            "total_income": 1500, "total_expenses": 900, "total_refunds": 0,
            "total_investments": 0, "total_transfers": 0, "net_cash_flow": 600,
            "total_transactions": 3, "category_summary": {"Food": 900},
            "top_merchants": [{"merchant": "Cafe", "amount": 500}],
        }}
        response = '{"headline":"A steady week","insights":["Keep an eye on food spending"],"disclaimer":"Educational only."}'

        with patch("routes.ai_settings.is_ai_configured", return_value=True), \
             patch("routes.ai_settings.get_ai_configuration", return_value=SimpleNamespace(provider="gemini", model="test-model")), \
             patch("routes.ai_settings.dashboard_summary", return_value=dashboard_result) as summary, \
             patch("routes.ai_settings.get_profile_ai_preferences", return_value={}), \
             patch("routes.ai_settings.generate_text", return_value=response), \
             patch("routes.ai_settings.ai_insights_collection.insert_one") as insert_one:
            result = generate_weekly_digest()

        self.assertEqual(result["insight"]["headline"], "A steady week")
        self.assertIn("date_from", summary.call_args.kwargs)
        self.assertEqual(insert_one.call_args.args[0]["kind"], "weekly_digest")

    def test_weekly_digest_uses_local_guidance_when_provider_is_unavailable(self):
        dashboard_result = {"status": "success", "summary": {
            "total_spend": 900, "total_credit": 1500, "net_balance": 600,
            "total_income": 1500, "total_expenses": 900, "total_refunds": 0,
            "total_investments": 0, "total_transfers": 0, "net_cash_flow": 600,
            "total_transactions": 3, "category_summary": {"Food": 900},
            "top_merchants": [{"merchant": "Cafe", "amount": 500}],
        }}

        with patch("routes.ai_settings.is_ai_configured", return_value=True), \
             patch("routes.ai_settings.get_ai_configuration", return_value=SimpleNamespace(provider="gemini", model="test-model")), \
             patch("routes.ai_settings.dashboard_summary", return_value=dashboard_result), \
             patch("routes.ai_settings.get_profile_ai_preferences", return_value={}), \
             patch("routes.ai_settings.generate_text", side_effect=AIProviderError("quota unavailable")), \
             patch("routes.ai_settings.ai_insights_collection.insert_one") as insert_one:
            result = generate_weekly_digest()

        self.assertEqual(result["source"], "rule_based")
        self.assertTrue(result["insight"]["insights"])
        self.assertEqual(insert_one.call_args.args[0]["source"], "rule_based")
