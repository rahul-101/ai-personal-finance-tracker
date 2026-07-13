from fastapi import APIRouter
from services.gemini_ai import analyze_transaction_email_with_gemini


router = APIRouter()


@router.get("/ai/gemini-test")
def gemini_test():
    subject = "Transaction Alert"
    sender = "alerts@bank.com"

    masked_email_text = "INR 849.00 was spent at SWIGGY using your card XX1234 on 2026-07-02."

    rule_based_data = {
        "is_transaction": True,
        "date": "2026-07-02",
        "merchant": "Swiggy",
        "amount": 849.00,
        "category": "Food",
        "source": "email",
        "transaction_type": "debit"
    }

    result = analyze_transaction_email_with_gemini(
        subject=subject,
        sender=sender,
        masked_email_text=masked_email_text,
        rule_based_data=rule_based_data
    )

    return {
        "status": "success",
        "gemini_result": result
    }