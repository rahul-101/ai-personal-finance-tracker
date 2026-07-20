from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from datetime import date as Date, datetime, timezone
from typing import Literal
from pydantic import ValidationError

from models import GmailLogReviewDecision, Transaction, TransactionReviewDecision
from database import gmail_logs_collection, transactions_collection

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
    transaction_type: Literal["debit", "credit", "income", "expense", "investment", "transfer", "refund"] | None = Query(default=None),
    date_from: Date | None = Query(default=None),
    date_to: Date | None = Query(default=None),
):
    """
    Fetch all transactions from MongoDB.
    """

    try:
        # FastAPI resolves omitted Query defaults to None at runtime; normalize
        # direct function calls too, which retain the Query descriptor.
        status = status if isinstance(status, str) else None
        transaction_type = transaction_type if isinstance(transaction_type, str) else None
        date_from = date_from if isinstance(date_from, Date) else None
        date_to = date_to if isinstance(date_to, Date) else None
        if date_from and date_to and date_from > date_to:
            raise HTTPException(status_code=422, detail="date_from must be on or before date_to")

        conditions = []
        if status == "confirmed":
            # Older manual records predate review statuses and remain confirmed.
            conditions.append({"$or": [{"status": "confirmed"}, {"status": {"$exists": False}}]})
        elif status:
            conditions.append({"status": status})

        if transaction_type:
            conditions.append({"transaction_type": transaction_type})

        date_query = {}
        if date_from:
            date_query["$gte"] = date_from.isoformat()
        if date_to:
            date_query["$lte"] = date_to.isoformat()
        if date_query:
            conditions.append({"date": date_query})

        query = {} if not conditions else conditions[0] if len(conditions) == 1 else {"$and": conditions}

        transactions = list(
            transactions_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string.
        transactions = [convert_mongo_document(tx) for tx in transactions]

        filters = {"status": status}
        if transaction_type:
            filters["transaction_type"] = transaction_type
        if date_from:
            filters["date_from"] = date_from.isoformat()
        if date_to:
            filters["date_to"] = date_to.isoformat()

        return {
            "status": "success",
            "count": len(transactions),
            "filter": filters,
            "transactions": transactions
        }

    except HTTPException:
        raise
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


@router.patch("/gmail-review-logs/{log_id}")
def review_gmail_log(log_id: str, review: GmailLogReviewDecision):
    """Create or discard a transaction that was held back by low AI confidence."""
    object_id = get_transaction_object_id(log_id)
    log = gmail_logs_collection.find_one({"_id": object_id})
    if not log:
        raise HTTPException(status_code=404, detail="Gmail review item not found")
    if log.get("status") != "review_required_not_inserted":
        raise HTTPException(status_code=409, detail="This Gmail review item has already been resolved")

    now = datetime.now(timezone.utc)
    if review.decision == "reject":
        gmail_logs_collection.update_one(
            {"_id": object_id, "status": "review_required_not_inserted"},
            {"$set": {"status": "review_rejected", "reviewed_at": now, "review_note": review.review_note}},
        )
        return {"status": "success", "message": "Gmail email ignored"}

    proposed = log.get("proposed_transaction", {})
    corrections = review.model_dump(
        include={"date", "merchant", "amount", "category", "transaction_type"},
        exclude_none=True,
        mode="json",
    )
    try:
        transaction = Transaction(
            **{
                **proposed,
                **corrections,
                "source": "email",
                "status": "confirmed",
            }
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail="Enter a date, merchant, positive amount, category, and transaction type before adding this email.",
        ) from error

    gmail_message_id = log.get("gmail_message_id")
    if gmail_message_id and transactions_collection.find_one({"gmail_message_id": gmail_message_id}):
        raise HTTPException(status_code=409, detail="A transaction already exists for this Gmail email")

    transaction_data = transaction.model_dump(mode="json")
    transaction_data.update(
        {
            "created_at": now,
            "gmail_message_id": gmail_message_id,
            "email_sender": log.get("from", ""),
            "review_note": review.review_note,
            "reviewed_at": now,
        }
    )
    result = transactions_collection.insert_one(transaction_data)
    transaction_data["_id"] = result.inserted_id
    updated_log = gmail_logs_collection.find_one_and_update(
        {"_id": object_id, "status": "review_required_not_inserted"},
        {"$set": {"status": "review_approved", "reviewed_at": now, "review_note": review.review_note, "transaction_id": str(result.inserted_id)}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_log:
        raise HTTPException(status_code=409, detail="This Gmail review item was already resolved")

    return {"status": "success", "message": "Transaction added from Gmail review", "transaction": convert_mongo_document(transaction_data)}
