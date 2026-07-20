import json
import re
from pydantic import ValidationError

from models import AIEmailAnalysis
from services.ai_client import generate_text, is_ai_configured


DEFAULT_CATEGORIES = [
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
    "Others"
]


def extract_json_from_text(response_text: str) -> dict:
    if not response_text:
        return {}

    try:
        return json.loads(response_text)
    except Exception:
        pass

    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            return {}

    return {}


def fallback_ai_result(rule_based_data: dict) -> dict:
    return {
        "is_transaction": rule_based_data.get("is_transaction", False),
        "ignore_reason": rule_based_data.get("ignore_reason", ""),
        "date": rule_based_data.get("date"),
        "merchant": rule_based_data.get("merchant", "Unknown"),
        "amount": rule_based_data.get("amount", 0),
        "category": rule_based_data.get("category", "Others"),
        "source": "email",
        "transaction_type": rule_based_data.get("transaction_type", "debit"),
        "confidence": 0.70,
        "payment_mode": "unknown",
        "masked_account": "",
        "reason": "AI provider not configured or failed. Rule-based fallback used."
    }


def validate_ai_result(candidate: dict, fallback: dict) -> dict:
    """Merge AI output with safe defaults, then reject invalid domain data."""
    merged_result = fallback.copy()
    merged_result.update(candidate)

    try:
        return AIEmailAnalysis.model_validate(merged_result).model_dump(mode="json")
    except ValidationError:
        fallback["reason"] = "AI provider returned invalid finance data. Rule-based fallback used."
        return fallback


def analyze_transaction_email(
    subject: str,
    sender: str,
    masked_email_text: str,
    rule_based_data: dict
) -> dict:
    if not is_ai_configured():
        return fallback_ai_result(rule_based_data)

    prompt = f"""
You are an AI assistant for a personal finance tracker.

Your job is to analyze a masked Gmail email and decide whether it is a real financial transaction.

Ignore these emails:
- OTP emails
- Password reset emails
- Login/security alerts
- Promotional emails
- Loan offers
- Credit card offers
- Cashback offers
- Advertisements
- Newsletters
- Emails without real money movement

Return JSON only. Do not include markdown. Do not include explanation outside JSON.

Required JSON schema:
{{
  "is_transaction": true,
  "ignore_reason": "",
  "date": "YYYY-MM-DD or empty string",
  "merchant": "merchant name",
  "amount": 0,
  "category": "Food or Shopping or Transport or Bills or Groceries or Entertainment or Health or Travel or Education or Income or Refund or Investment or Transfer or Others",
  "source": "email",
  "transaction_type": "income or expense or investment or transfer or refund (legacy debit or credit is also allowed)",
  "confidence": 0.0,
  "payment_mode": "card or upi or netbanking or wallet or cash or unknown",
  "masked_account": "masked account/card if available",
  "reason": "short reason for classification"
}}

Subject:
{subject}

Sender:
{sender}

Rule based extraction:
{json.dumps(rule_based_data, ensure_ascii=False)}

Masked email text:
{masked_email_text[:3000]}
"""

    try:
        response_text = generate_text(prompt)

        parsed_json = extract_json_from_text(response_text)

        if not parsed_json:
            return fallback_ai_result(rule_based_data)

        return validate_ai_result(
            candidate=parsed_json,
            fallback=fallback_ai_result(rule_based_data),
        )

    except Exception as error:
        fallback = fallback_ai_result(rule_based_data)
        fallback["reason"] = f"AI provider error. Rule-based fallback used. Error: {str(error)}"
        return fallback
