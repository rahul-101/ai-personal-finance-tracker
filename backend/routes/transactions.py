from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from datetime import datetime, timezone
from typing import Literal

from models import Transaction, TransactionReviewDecision
from database import transactions_collection

# APIRouter helps organize APIs in separate files.
router = APIRouter()


def convert_mongo_document(document):
    """
    MongoDB returns _id as ObjectId, which is not directly JSON serializable.
    This function converts _id to string.
    """
    serialized_document = document.copy()
    serialized_document["_id"] = str(serialized_document["_id"])

    created_at = serialized_document.get("created_at")
    if isinstance(created_at, datetime):
        serialized_document["created_at"] = created_at.isoformat()

    return serialized_document


def get_transaction_object_id(transaction_id: str) -> ObjectId:
    try:
        return ObjectId(transaction_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")


@router.post("/transactions")
def add_transaction(transaction: Transaction):
    """
    Add a new transaction to MongoDB.

    Request body example:
    {
      "date": "2026-07-02",
      "merchant": "Amazon",
      "amount": 999,
      "category": "Shopping",
      "source": "email"
    }
    """

    try:
        # Convert Pydantic model to dictionary.
        transaction_data = transaction.model_dump(mode="json")

        # Add created timestamp.
        transaction_data["created_at"] = datetime.now(timezone.utc)

        # Insert document into MongoDB collection.
        result = transactions_collection.insert_one(transaction_data)

        return {
            "status": "success",
            "message": "Transaction added successfully",
            "inserted_id": str(result.inserted_id)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add transaction: {str(error)}"
        )


@router.get("/transactions")
def get_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    status: Literal["review_required", "confirmed", "rejected"] | None = Query(default=None),
):
    """
    Fetch all transactions from MongoDB.
    """

    try:
        query = {}
        if status == "confirmed":
            # Older manual records predate review statuses and remain confirmed.
            query = {"$or": [{"status": "confirmed"}, {"status": {"$exists": False}}]}
        elif status:
            query = {"status": status}

        transactions = list(
            transactions_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string.
        transactions = [convert_mongo_document(tx) for tx in transactions]

        return {
            "status": "success",
            "count": len(transactions),
            "filter": {"status": status},
            "transactions": transactions
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transactions: {str(error)}"
        )


@router.patch("/transactions/{transaction_id}/review")
def review_transaction(
    transaction_id: str,
    review: TransactionReviewDecision,
):
    """Approve or reject a transaction that an AI workflow flagged for review."""
    object_id = get_transaction_object_id(transaction_id)

    existing_transaction = transactions_collection.find_one({"_id": object_id})
    if not existing_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if existing_transaction.get("status") != "review_required":
        raise HTTPException(
            status_code=409,
            detail="Only review_required transactions can be reviewed",
        )

    update_fields = {
        "status": "confirmed" if review.decision == "approve" else "rejected",
        "review_decision": review.decision,
        "reviewed_at": datetime.now(timezone.utc),
    }

    if review.review_note:
        update_fields["review_note"] = review.review_note

    if review.decision == "approve":
        corrections = review.model_dump(
            include={"date", "merchant", "amount", "category", "transaction_type"},
            exclude_none=True,
            mode="json",
        )
        update_fields.update(corrections)

    updated_transaction = transactions_collection.find_one_and_update(
        {"_id": object_id, "status": "review_required"},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )

    if not updated_transaction:
        raise HTTPException(
            status_code=409,
            detail="Transaction was already reviewed by another request",
        )

    return {
        "status": "success",
        "message": f"Transaction {review.decision}d successfully",
        "transaction": convert_mongo_document(updated_transaction),
    }
