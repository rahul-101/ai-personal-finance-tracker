import unittest
from unittest.mock import Mock, patch

from routes.gmail_sync import record_sync_run


class GmailSyncRunTests(unittest.TestCase):
    def test_records_a_safe_summary_for_a_scheduled_sync(self):
        collection = Mock()

        with patch("routes.gmail_sync.gmail_sync_runs_collection", collection):
            record_sync_run("scheduled", "success", {"inserted_transactions": 2})

        document = collection.insert_one.call_args.args[0]
        self.assertEqual(document["source"], "scheduled")
        self.assertEqual(document["status"], "success")
        self.assertEqual(document["summary"], {"inserted_transactions": 2})
        self.assertNotIn("credentials", document)
