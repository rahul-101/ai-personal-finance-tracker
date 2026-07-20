import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from models import PersonalProfile
from routes.profile import get_profile, save_profile


class ProfileRouteTests(unittest.TestCase):
    def test_returns_null_when_single_user_profile_has_not_been_created(self):
        collection = Mock()
        collection.find_one.return_value = None

        with patch("routes.profile.profile_collection", collection):
            result = get_profile()

        self.assertIsNone(result["profile"])

    def test_saves_normalized_non_sensitive_profile_preferences(self):
        collection = Mock()
        collection.find_one.return_value = {
            "scope": "single_user", "display_name": "Rahul", "email": "rahul@example.com",
            "currency": "INR", "timezone": "Asia/Kolkata", "priorities": ["Save"], "account_labels": ["Savings"],
        }
        profile = PersonalProfile(
            display_name=" Rahul ", email=" RAHUL@example.com ", priorities=["Save", " Save "], account_labels=["Savings"],
        )

        with patch("routes.profile.profile_collection", collection):
            result = save_profile(profile)

        self.assertEqual(result["profile"]["display_name"], "Rahul")
        self.assertEqual(result["profile"]["email"], "rahul@example.com")
        self.assertEqual(collection.update_one.call_args.args[0], {"scope": "single_user"})
        self.assertEqual(profile.gmail_sync_frequency, "manual")

    def test_returns_scheduled_sync_status_with_an_iso_timestamp(self):
        collection = Mock()
        collection.find_one.return_value = {
            "scope": "single_user", "display_name": "Rahul",
            "last_gmail_scheduled_sync_at": datetime(2026, 7, 20, 10, 30, tzinfo=timezone.utc),
            "last_gmail_scheduled_sync_status": "success",
        }

        with patch("routes.profile.profile_collection", collection):
            result = get_profile()

        self.assertEqual(result["profile"]["last_gmail_scheduled_sync_status"], "success")
        self.assertEqual(result["profile"]["last_gmail_scheduled_sync_at"], "2026-07-20T10:30:00+00:00")
