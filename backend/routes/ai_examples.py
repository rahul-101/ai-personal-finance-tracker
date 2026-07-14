from fastapi import APIRouter
from services.ai_analysis import analyze_transaction_email


router = APIRouter()


@router.get("/ai/example-analysis")
def example_analysis():
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

    result = analyze_transaction_email(
        subject=subject,
        sender=sender,
        masked_email_text=masked_email_text,
        rule_based_data=rule_based_data
    )

    return {
        "status": "success",
        "analysis_result": result
    }
