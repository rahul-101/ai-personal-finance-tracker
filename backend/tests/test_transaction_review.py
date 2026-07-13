import unittest
from unittest.mock import patch

from bson import ObjectId
from fastapi import HTTPException

from models import TransactionReviewDecision
from routes.transactions import review_transaction


class FakeTransactionsCollection:
    def __init__(self, transaction: dict):
        self.transaction = transaction
        self.last_update = None

    def find_one(self, query: dict):
        if query.get("_id") == self.transaction["_id"]:
            return self.transaction.copy()
        return None

    def find_one_and_update(self, query: dict, update: dict, return_document):
        if (
            query.get("_id") != self.transaction["_id"]
            or query.get("status") != self.transaction["status"]
        ):
            return None

        self.last_update = update
        self.transaction.update(update["$set"])
        return self.transaction.copy()


class TransactionReviewRouteTests(unittest.TestCase):
    def setUp(self):
        self.transaction = {
            "_id": ObjectId(),
            "date": "2026-07-13",
            "merchant": "Unknown Receipt Merchant",
            "amount": 899.0,
            "category": "Others",
            "source": "receipt",
            "status": "review_required",
        }
        self.collection = FakeTransactionsCollection(self.transaction)

    def test_approval_confirms_and_applies_corrections(self):
        decision = TransactionReviewDecision(
            decision="approve",
            merchant="Coffee House",
            amount=799.0,
            category="Food",
            review_note="Corrected from receipt total",
        )

        with patch("routes.transactions.transactions_collection", self.collection):
            result = review_transaction(str(self.transaction["_id"]), decision)

        self.assertEqual(result["transaction"]["status"], "confirmed")
        self.assertEqual(result["transaction"]["merchant"], "Coffee House")
        self.assertEqual(result["transaction"]["amount"], 799.0)
        self.assertEqual(self.collection.last_update["$set"]["review_decision"], "approve")

    def test_rejection_preserves_original_financial_values(self):
        decision = TransactionReviewDecision(decision="reject", review_note="Not a receipt")

        with patch("routes.transactions.transactions_collection", self.collection):
            result = review_transaction(str(self.transaction["_id"]), decision)

        self.assertEqual(result["transaction"]["status"], "rejected")
        self.assertEqual(result["transaction"]["amount"], 899.0)
        self.assertEqual(self.collection.last_update["$set"]["review_decision"], "reject")

    def test_finalized_transaction_cannot_be_reviewed_again(self):
        self.transaction["status"] = "confirmed"

        with patch("routes.transactions.transactions_collection", self.collection):
            with self.assertRaises(HTTPException) as context:
                review_transaction(
                    str(self.transaction["_id"]),
                    TransactionReviewDecision(decision="approve"),
                )

        self.assertEqual(context.exception.status_code, 409)
