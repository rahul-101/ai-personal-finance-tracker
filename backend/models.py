from datetime import date as Date
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


class Transaction(BaseModel):
    """
    This model validates incoming transaction data.

    Example:
    {
      "date": "2026-07-02",
      "merchant": "Amazon",
      "amount": 999,
      "category": "Shopping",
      "source": "email"
    }
    """

    date: Date = Field(..., description="Transaction date in YYYY-MM-DD format")
    merchant: str = Field(..., min_length=1, max_length=120, description="Merchant or vendor name")
    amount: float = Field(..., gt=0, allow_inf_nan=False, description="Positive transaction amount")
    category: str = Field(..., min_length=1, max_length=60, description="Expense category")
    source: Literal["manual", "email", "receipt", "bill"] = Field(
        ..., description="How this transaction was created"
    )
    transaction_type: Literal["debit", "credit", "income", "expense", "investment", "transfer", "refund"] = "debit"
    status: Literal["confirmed", "review_required", "rejected"] = "confirmed"
    notes: Optional[str] = Field(default=None, max_length=1_000, description="Optional notes")

    @field_validator("merchant", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("notes")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class AIEmailAnalysis(BaseModel):
    """The provider-neutral AI email-analysis shape the application trusts."""

    model_config = ConfigDict(extra="forbid")

    is_transaction: bool
    ignore_reason: str = Field(default="", max_length=300)
    date: Date | None = None
    merchant: str = Field(default="Unknown", min_length=1, max_length=120)
    amount: float = Field(default=0, ge=0, allow_inf_nan=False)
    category: Literal[
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Groceries",
        "Entertainment",
        "Health",
        "Travel",
        "Education",
        "Income",
        "Refund",
        "Investment",
        "Transfer",
        "Cash Withdrawal",
        "Others",
    ] = "Others"
    source: Literal["email"] = "email"
    transaction_type: Literal["debit", "credit", "income", "expense", "investment", "transfer", "refund", "bill", "unknown"] = "debit"
    confidence: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    payment_mode: Literal["card", "upi", "netbanking", "wallet", "cash", "unknown"] = "unknown"
    masked_account: str = Field(default="", max_length=50)
    reason: str = Field(default="", max_length=500)

    @field_validator("merchant")
    @classmethod
    def normalize_merchant(cls, value: str) -> str:
        return value.strip() or "Unknown"


# Backwards-compatible name for external code using the earlier Gemini-only model.
GeminiEmailAnalysis = AIEmailAnalysis


class TransactionReviewDecision(BaseModel):
    """A human decision for a transaction previously flagged for review."""

    decision: Literal["approve", "reject"]
    review_note: str | None = Field(default=None, max_length=500)
    date: Date | None = None
    merchant: str | None = Field(default=None, min_length=1, max_length=120)
    amount: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    transaction_type: Literal["debit", "credit", "income", "expense", "investment", "transfer", "refund"] | None = None

    @field_validator("review_note", "merchant", "category")
    @classmethod
    def strip_optional_review_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class GmailLogReviewDecision(TransactionReviewDecision):
    """Human decision for a Gmail email held back before a transaction was created."""

    model_config = ConfigDict(extra="forbid")


class MonthlyBudget(BaseModel):
    """Single-user monthly limits, optionally split by spending category."""

    monthly_limit: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    category_limits: dict[str, float] = Field(default_factory=dict)

    @field_validator("category_limits")
    @classmethod
    def normalize_category_limits(cls, value: dict[str, float]) -> dict[str, float]:
        normalized = {}
        for category, limit in value.items():
            cleaned_category = category.strip()
            if not cleaned_category:
                raise ValueError("Budget categories cannot be blank")
            if not math.isfinite(limit) or limit <= 0:
                raise ValueError("Each category budget must be a positive number")
            normalized[cleaned_category] = limit
        return normalized


class PersonalProfile(BaseModel):
    """Non-sensitive single-user preferences for setup and personalized insights."""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=254)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=64)
    monthly_income_target: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    savings_goal: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    investment_goal: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    starting_balance: float | None = Field(default=None, allow_inf_nan=False)
    priorities: list[str] = Field(default_factory=list, max_length=8)
    account_labels: list[str] = Field(default_factory=list, max_length=12)
    gmail_sync_frequency: Literal["manual", "daily", "weekly"] = "manual"

    @field_validator("display_name", "currency", "timezone")
    @classmethod
    def normalize_required_profile_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value.upper() if len(value) == 3 else value

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not value:
            return None
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("priorities", "account_labels")
    @classmethod
    def normalize_profile_lists(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in values if item.strip()))
