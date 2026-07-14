from datetime import date as Date
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
    transaction_type: Literal["debit", "credit"] = "debit"
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
        "Cash Withdrawal",
        "Others",
    ] = "Others"
    source: Literal["email"] = "email"
    transaction_type: Literal["debit", "credit", "refund", "bill", "unknown"] = "debit"
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
    transaction_type: Literal["debit", "credit"] | None = None

    @field_validator("review_note", "merchant", "category")
    @classmethod
    def strip_optional_review_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
