import unittest
from unittest.mock import Mock, patch

from routes.gmail_auth import gmail_status


class GmailStatusTests(unittest.TestCase):
    def test_backfills_and_returns_connected_gmail_address(self):
        collection = Mock()
        collection.find_one.return_value = {"user_id": "demo-user", "provider": "gmail", "encrypted_token_json": "token"}

        with patch("routes.gmail_auth.gmail_tokens_collection", collection), \
             patch("routes.gmail_auth.load_gmail_credentials", return_value=Mock()), \
             patch("routes.gmail_auth.get_connected_gmail_address", return_value="rahul@example.com"):
            result = gmail_status()

        self.assertTrue(result["connected"])
        self.assertEqual(result["email_address"], "rahul@example.com")
        self.assertEqual(collection.update_one.call_args.args[1]["$set"]["email_address"], "rahul@example.com")

    def test_reports_reconnect_required_when_token_is_invalid(self):
        collection = Mock()
        collection.find_one.return_value = {"user_id": "demo-user", "provider": "gmail", "encrypted_token_json": "token"}

        with patch("routes.gmail_auth.gmail_tokens_collection", collection), \
             patch("routes.gmail_auth.load_gmail_credentials", side_effect=Exception("invalid_grant")):
            result = gmail_status()

        self.assertFalse(result["connected"])
        self.assertTrue(result["reconnect_required"])
