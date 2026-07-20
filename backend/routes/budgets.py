from datetime import datetime, timezone
import re

from fastapi import APIRouter, HTTPException

from database import budgets_collection, transactions_collection
from models import MonthlyBudget
from routes.dashboard import classify_financial_type


router = APIRouter()


def current_month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def validate_month(month: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=422, detail="month must use YYYY-MM format")
    return month


def get_current_month_spending(month: str) -> tuple[float, dict[str, float]]:
    """Count only confirmed debit transactions for the selected calendar month."""
    transactions = transactions_collection.find({"date": {"$regex": f"^{month}"}})
    total_spend = 0.0
    category_spend: dict[str, float] = {}

    for transaction in transactions:
        if classify_financial_type(transaction.get("transaction_type", "debit")) != "expense":
            continue
        if transaction.get("status", "confirmed") != "confirmed":
            continue
        amount = float(transaction.get("amount", 0))
        category = transaction.get("category", "Others")
        total_spend += amount
        category_spend[category] = category_spend.get(category, 0) + amount

    return round(total_spend, 2), {category: round(amount, 2) for category, amount in category_spend.items()}


def build_budget_response(month: str | None = None) -> dict:
    month = validate_month(month) if month else current_month_key()
    budget = budgets_collection.find_one({"scope": "monthly", "month": month})
    if not budget and month == current_month_key():
        # Existing single-budget documents remain usable until the user saves again.
        budget = budgets_collection.find_one({"scope": "monthly", "month": {"$exists": False}})
    budget = budget or {}
    total_spend, category_spend = get_current_month_spending(month)
    monthly_limit = budget.get("monthly_limit")
    category_limits = budget.get("category_limits", {})

    categories = [
        {
            "category": category,
            "limit": limit,
            "spent": category_spend.get(category, 0),
            "remaining": round(limit - category_spend.get(category, 0), 2),
            "percent_used": round((category_spend.get(category, 0) / limit) * 100, 1),
        }
        for category, limit in sorted(category_limits.items())
    ]
    overall = None if monthly_limit is None else {
        "limit": monthly_limit,
        "spent": total_spend,
        "remaining": round(monthly_limit - total_spend, 2),
        "percent_used": round((total_spend / monthly_limit) * 100, 1),
    }
    return {"status": "success", "month": month, "overall": overall, "categories": categories}


@router.get("/budgets/current")
def get_current_budget():
    try:
        return build_budget_response()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load budget: {error}")


@router.put("/budgets/current")
def save_current_budget(budget: MonthlyBudget):
    return save_budget_for_month(current_month_key(), budget)


@router.get("/budgets/{month}")
def get_budget_for_month(month: str):
    try:
        return build_budget_response(month)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load budget: {error}")


@router.put("/budgets/{month}")
def save_budget_for_month(month: str, budget: MonthlyBudget):
    month = validate_month(month)
    try:
        budgets_collection.update_one(
            {"scope": "monthly", "month": month},
            {"$set": {"monthly_limit": budget.monthly_limit, "category_limits": budget.category_limits, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"scope": "monthly", "month": month}},
            upsert=True,
        )
        return build_budget_response(month)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to save budget: {error}")
