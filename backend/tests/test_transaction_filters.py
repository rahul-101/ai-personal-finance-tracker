import unittest
from datetime import date
from unittest.mock import Mock, patch

from fastapi import HTTPException
from routes.transactions import get_transactions


class _Cursor(list):
    def sort(self, *_):
        return self

    def skip(self, *_):
        return self

    def limit(self, *_):
        return self


class TransactionFilterTests(unittest.TestCase):
    def test_filters_transactions_by_financial_type(self):
        collection = Mock()
        collection.find.return_value = _Cursor()

        with patch("routes.transactions.transactions_collection", collection):
            result = get_transactions(transaction_type="investment")

        collection.find.assert_called_once_with({"transaction_type": "investment"})
        self.assertEqual(result["filter"], {"status": None, "transaction_type": "investment"})

    def test_combines_status_and_financial_type_filters(self):
        collection = Mock()
        collection.find.return_value = _Cursor()

        with patch("routes.transactions.transactions_collection", collection):
            get_transactions(status="review_required", transaction_type="expense")

        collection.find.assert_called_once_with({"$and": [{"status": "review_required"}, {"transaction_type": "expense"}]})

    def test_filters_transactions_by_inclusive_date_range(self):
        collection = Mock()
        collection.find.return_value = _Cursor()

        with patch("routes.transactions.transactions_collection", collection):
            result = get_transactions(date_from=date(2026, 7, 1), date_to=date(2026, 7, 31))

        collection.find.assert_called_once_with({"date": {"$gte": "2026-07-01", "$lte": "2026-07-31"}})
        self.assertEqual(result["filter"]["date_from"], "2026-07-01")
        self.assertEqual(result["filter"]["date_to"], "2026-07-31")

    def test_rejects_an_inverted_date_range(self):
        with self.assertRaises(HTTPException) as raised:
            get_transactions(date_from=date(2026, 8, 1), date_to=date(2026, 7, 1))

        self.assertEqual(raised.exception.status_code, 422)
