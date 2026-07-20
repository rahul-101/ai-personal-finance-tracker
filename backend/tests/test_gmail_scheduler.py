import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from services.gmail_scheduler import run_due_gmail_sync


class GmailSchedulerTests(unittest.TestCase):
    def test_manual_preference_never_runs_automatic_sync(self):
        collection = Mock()
        collection.find_one.return_value = {"gmail_sync_frequency": "manual"}

        with patch("services.gmail_scheduler.profile_collection", collection), \
             patch("services.gmail_scheduler.sync_gmail_transactions") as sync:
            result = run_due_gmail_sync(datetime(2026, 7, 20, tzinfo=timezone.utc))

        self.assertFalse(result["ran"])
        sync.assert_not_called()

    def test_daily_preference_runs_when_due_and_records_success(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        collection = Mock()
        collection.find_one.return_value = {"gmail_sync_frequency": "daily", "last_gmail_scheduled_sync_at": now - timedelta(days=1, minutes=1)}

        with patch("services.gmail_scheduler.profile_collection", collection), \
             patch("services.gmail_scheduler.sync_gmail_transactions", return_value={"summary": {"inserted_transactions": 2}}) as sync:
            result = run_due_gmail_sync(now)

        self.assertTrue(result["ran"])
        self.assertEqual(result["status"], "success")
        sync.assert_called_once_with(max_results=20, sync_source="scheduled")
        self.assertEqual(collection.update_one.call_args.args[1]["$set"]["last_gmail_scheduled_sync_status"], "success")
