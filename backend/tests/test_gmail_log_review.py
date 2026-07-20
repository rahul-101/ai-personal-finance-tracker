import unittest
from unittest.mock import Mock, patch

from bson import ObjectId

from models import GmailLogReviewDecision
from routes.transactions import review_gmail_log


class GmailLogReviewTests(unittest.TestCase):
    def test_reject_marks_a_gmail_review_item_as_ignored(self):
        logs = Mock()
        logs.find_one.return_value = {"status": "review_required_not_inserted"}

        with patch("routes.transactions.gmail_logs_collection", logs):
            result = review_gmail_log(str(ObjectId()), GmailLogReviewDecision(decision="reject"))

        self.assertEqual(result["message"], "Gmail email ignored")
        self.assertEqual(logs.update_one.call_args.args[1]["$set"]["status"], "review_rejected")

    def test_approval_creates_a_confirmed_transaction_from_the_proposal(self):
        logs = Mock()
        logs.find_one.return_value = {
            "status": "review_required_not_inserted",
            "gmail_message_id": "message-1",
            "from": "bank@example.com",
            "proposed_transaction": {
                "date": "2026-07-21", "merchant": "Coffee Shop", "amount": 125,
                "category": "Food", "transaction_type": "expense",
            },
        }
        logs.find_one_and_update.return_value = {"status": "review_approved"}
        transactions = Mock()
        transactions.find_one.return_value = None
        transactions.insert_one.return_value.inserted_id = ObjectId()

        with patch("routes.transactions.gmail_logs_collection", logs), \
             patch("routes.transactions.transactions_collection", transactions):
            result = review_gmail_log(str(ObjectId()), GmailLogReviewDecision(decision="approve"))

        self.assertEqual(result["message"], "Transaction added from Gmail review")
        inserted = transactions.insert_one.call_args.args[0]
        self.assertEqual(inserted["merchant"], "Coffee Shop")
        self.assertEqual(inserted["status"], "confirmed")
        self.assertEqual(logs.find_one_and_update.call_args.args[1]["$set"]["status"], "review_approved")
