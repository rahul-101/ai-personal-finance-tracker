import re

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime

from database import transactions_collection
from database import gmail_logs_collection
from database import gmail_sync_runs_collection
from database import bills_collection


router = APIRouter()


def convert_mongo_value(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def convert_mongo_document(document):
    converted_document = {}

    for key, value in document.items():
        converted_document[key] = convert_mongo_value(value)

    return converted_document


def get_month_from_transaction(transaction):
    date_value = transaction.get("date")

    if date_value and isinstance(date_value, str) and len(date_value) >= 7:
        return date_value[:7]

    created_at = transaction.get("created_at")

    if isinstance(created_at, datetime):
        return created_at.strftime("%Y-%m")

    return "Unknown"


def classify_financial_type(transaction_type: str) -> str:
    """Map legacy values into the richer single-user finance classifications."""
    return {
        "credit": "income",
        "income": "income",
        "refund": "refund",
        "investment": "investment",
        "transfer": "transfer",
        "debit": "expense",
        "expense": "expense",
        "bill": "expense",
        "unknown": "expense",
    }.get(transaction_type, "expense")


@router.get("/dashboard/summary")
def dashboard_summary(month: str | None = None):
    if month and not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=422, detail="month must use YYYY-MM format")

    try:
        transactions = list(transactions_collection.find())
        if month:
            transactions = [transaction for transaction in transactions if get_month_from_transaction(transaction) == month]

        total_expenses = 0
        total_income = 0
        total_refunds = 0
        total_investments = 0
        total_transfers = 0
        total_transactions = len(transactions)
        review_required_count = 0

        category_summary = {}
        source_summary = {}
        merchant_summary = {}
        monthly_summary = {}

        for tx in transactions:
            amount = float(tx.get("amount", 0))
            financial_type = classify_financial_type(tx.get("transaction_type", "debit"))
            category = tx.get("category", "Others")
            source = tx.get("source", "unknown")
            merchant = tx.get("merchant", "Unknown")
            status = tx.get("status", "confirmed")
            month_key = get_month_from_transaction(tx)

            if status == "review_required":
                review_required_count = review_required_count + 1

            if financial_type == "income":
                total_income = total_income + amount
            elif financial_type == "refund":
                total_refunds = total_refunds + amount
            elif financial_type == "investment":
                total_investments = total_investments + amount
            elif financial_type == "transfer":
                total_transfers = total_transfers + amount
            else:
                total_expenses = total_expenses + amount

                category_summary[category] = category_summary.get(category, 0) + amount
                merchant_summary[merchant] = merchant_summary.get(merchant, 0) + amount
                monthly_summary[month_key] = monthly_summary.get(month_key, 0) + amount

            source_summary[source] = source_summary.get(source, 0) + 1

        ignored_email_count = gmail_logs_collection.count_documents(
            {
                "status": {
                    "$regex": "^ignored"
                }
            }
        )

        review_log_count = gmail_logs_collection.count_documents(
            {
                "status": "review_required_not_inserted"
            }
        )

        bills_due_count = bills_collection.count_documents(
            {
                "status": {
                    "$ne": "paid"
                }
            }
        )

        top_merchants = []

        for merchant, amount in merchant_summary.items():
            top_merchants.append(
                {
                    "merchant": merchant,
                    "amount": round(amount, 2)
                }
            )

        top_merchants = sorted(
            top_merchants,
            key=lambda item: item["amount"],
            reverse=True
        )

        monthly_trend = []

        for month, amount in monthly_summary.items():
            monthly_trend.append(
                {
                    "month": month,
                    "amount": round(amount, 2)
                }
            )

        monthly_trend = sorted(
            monthly_trend,
            key=lambda item: item["month"]
        )

        return {
            "status": "success",
            "summary": {
                # Legacy fields are retained for existing clients.
                "total_spend": round(total_expenses, 2),
                "total_credit": round(total_income + total_refunds, 2),
                "net_balance": round(total_income + total_refunds - total_expenses - total_investments, 2),
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "total_refunds": round(total_refunds, 2),
                "total_investments": round(total_investments, 2),
                "total_transfers": round(total_transfers, 2),
                "net_cash_flow": round(total_income + total_refunds - total_expenses - total_investments, 2),
                "total_transactions": total_transactions,
                "selected_month": month,
                "review_required_count": review_required_count,
                "ignored_email_count": ignored_email_count,
                "review_log_count": review_log_count,
                "bills_due_count": bills_due_count,
                "category_summary": category_summary,
                "source_summary": source_summary,
                "top_merchants": top_merchants[:10],
                "monthly_trend": monthly_trend
            }
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load dashboard summary: {str(error)}"
        )


@router.get("/dashboard/latest-transactions")
def latest_transactions(limit: int = 20):
    try:
        transactions = list(
            transactions_collection.find()
            .sort("created_at", -1)
            .limit(limit)
        )

        converted_transactions = [
            convert_mongo_document(tx) for tx in transactions
        ]

        return {
            "status": "success",
            "count": len(converted_transactions),
            "transactions": converted_transactions
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load latest transactions: {str(error)}"
        )


@router.get("/dashboard/gmail-logs")
def dashboard_gmail_logs(limit: int = 20):
    try:
        logs = list(
            gmail_logs_collection.find()
            .sort("created_at", -1)
            .limit(limit)
        )

        converted_logs = [
            convert_mongo_document(log) for log in logs
        ]

        return {
            "status": "success",
            "count": len(converted_logs),
            "logs": converted_logs
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load Gmail logs: {str(error)}"
        )


@router.get("/dashboard/gmail-sync-runs")
def dashboard_gmail_sync_runs(limit: int = 10):
    try:
        runs = list(gmail_sync_runs_collection.find().sort("created_at", -1).limit(limit))
        return {
            "status": "success",
            "count": len(runs),
            "runs": [convert_mongo_document(run) for run in runs],
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to load Gmail sync runs: {str(error)}")


@router.get("/dashboard/review-required")
def review_required_transactions(limit: int = 50):
    try:
        transactions = list(
            transactions_collection.find(
                {
                    "status": "review_required"
                }
            )
            .sort("created_at", -1)
            .limit(limit)
        )

        converted_transactions = [
            convert_mongo_document(tx) for tx in transactions
        ]

        logs = list(
            gmail_logs_collection.find(
                {
                    "status": "review_required_not_inserted"
                }
            )
            .sort("created_at", -1)
            .limit(limit)
        )

        converted_logs = [
            convert_mongo_document(log) for log in logs
        ]

        return {
            "status": "success",
            "transactions_count": len(converted_transactions),
            "logs_count": len(converted_logs),
            "transactions": converted_transactions,
            "logs": converted_logs
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load review required data: {str(error)}"
        )


@router.get("/dashboard/bills-due")
def bills_due(limit: int = 50):
    try:
        bills = list(
            bills_collection.find(
                {
                    "status": {
                        "$ne": "paid"
                    }
                }
            )
            .sort("created_at", -1)
            .limit(limit)
        )

        converted_bills = [
            convert_mongo_document(bill) for bill in bills
        ]

        total_due_amount = 0

        for bill in bills:
            total_due_amount = total_due_amount + float(bill.get("amount", 0))

        return {
            "status": "success",
            "count": len(converted_bills),
            "total_due_amount": round(total_due_amount, 2),
            "bills": converted_bills
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load bills due: {str(error)}"
        )
