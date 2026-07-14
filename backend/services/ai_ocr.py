"""Provider-neutral receipt and bill analysis backed by services.ai_client."""

import json
import re
from services.ai_client import generate_text, is_ai_configured


def extract_json_from_response(response_text: str) -> dict:
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


def fallback_receipt_result(ocr_text: str, fallback_merchant: str, fallback_amount) -> dict:
    return {
        "is_valid_receipt": True,
        "merchant": fallback_merchant or "Unknown Receipt Merchant",
        "amount": float(fallback_amount or 0),
        "currency": "INR",
        "date": "",
        "category": "Others",
        "payment_mode": "unknown",
        "confidence": 0.65,
        "reason": "AI provider unavailable or failed. Rule-based OCR fallback used."
    }


def fallback_bill_result(ocr_text: str, fallback_provider: str, fallback_amount, fallback_due_date) -> dict:
    return {
        "is_valid_bill": True,
        "provider": fallback_provider or "Unknown Bill Provider",
        "bill_type": "Bill",
        "amount": float(fallback_amount or 0),
        "currency": "INR",
        "bill_date": "",
        "due_date": fallback_due_date or "",
        "category": "Bills",
        "confidence": 0.65,
        "reason": "AI provider unavailable or failed. Rule-based OCR fallback used."
    }


def analyze_receipt_ocr(
    ocr_text: str,
    fallback_merchant: str,
    fallback_amount
) -> dict:
    fallback = fallback_receipt_result(
        ocr_text=ocr_text,
        fallback_merchant=fallback_merchant,
        fallback_amount=fallback_amount
    )

    if not is_ai_configured():
        return fallback

    prompt = f"""
You are an AI receipt extraction assistant for a personal finance tracker.

Analyze the OCR text from a receipt image.

Return JSON only. Do not include markdown. Do not include explanation outside JSON.

Important rules:
- Extract only an actual customer purchase receipt.
- If text is not a receipt, set is_valid_receipt to false.
- Use the final payable amount or grand total as amount.
- Do not use phone numbers, GST numbers, invoice numbers, or item quantities as amount.
- If merchant is unclear, use "Unknown Receipt Merchant".
- Category must be one of:
  Food, Shopping, Transport, Bills, Groceries, Entertainment, Health, Travel, Education, Others.

Required JSON schema:
{{
  "is_valid_receipt": true,
  "merchant": "merchant name",
  "amount": 0,
  "currency": "INR",
  "date": "YYYY-MM-DD or empty string",
  "category": "Food",
  "payment_mode": "card or upi or cash or wallet or unknown",
  "confidence": 0.0,
  "reason": "short reason"
}}

OCR text:
{ocr_text[:4000]}
"""

    try:
        response_text = generate_text(prompt)

        parsed = extract_json_from_response(response_text)

        if not parsed:
            return fallback

        final_result = fallback.copy()
        final_result.update(parsed)

        if not final_result.get("merchant"):
            final_result["merchant"] = fallback["merchant"]

        if not final_result.get("amount"):
            final_result["amount"] = fallback["amount"]

        if not final_result.get("category"):
            final_result["category"] = "Others"

        if not final_result.get("confidence"):
            final_result["confidence"] = 0.70

        return final_result

    except Exception as error:
        fallback["reason"] = f"AI provider receipt extraction failed. Fallback used. Error: {str(error)}"
        return fallback


def analyze_bill_ocr(
    ocr_text: str,
    fallback_provider: str,
    fallback_amount,
    fallback_due_date
) -> dict:
    fallback = fallback_bill_result(
        ocr_text=ocr_text,
        fallback_provider=fallback_provider,
        fallback_amount=fallback_amount,
        fallback_due_date=fallback_due_date
    )

    if not is_ai_configured():
        return fallback

    prompt = f"""
You are an AI bill extraction assistant for a personal finance tracker.

Analyze the OCR text from a bill image.

Return JSON only. Do not include markdown. Do not include explanation outside JSON.

Important rules:
- Extract only actual bill/payment due information.
- If text is not a bill, set is_valid_bill to false.
- Use the payable amount, amount due, bill amount, or total due as amount.
- Do not use phone numbers, consumer IDs, account numbers, invoice numbers, taxes, or previous balance unless it is the final payable amount.
- due_date should be extracted only if clearly present.
- Category must usually be Bills.

Required JSON schema:
{{
  "is_valid_bill": true,
  "provider": "provider name",
  "bill_type": "electricity or mobile or broadband or gas or water or credit card or rent or subscription or other",
  "amount": 0,
  "currency": "INR",
  "bill_date": "YYYY-MM-DD or empty string",
  "due_date": "YYYY-MM-DD or empty string",
  "category": "Bills",
  "confidence": 0.0,
  "reason": "short reason"
}}

OCR text:
{ocr_text[:4000]}
"""

    try:
        response_text = generate_text(prompt)

        parsed = extract_json_from_response(response_text)

        if not parsed:
            return fallback

        final_result = fallback.copy()
        final_result.update(parsed)

        if not final_result.get("provider"):
            final_result["provider"] = fallback["provider"]

        if not final_result.get("amount"):
            final_result["amount"] = fallback["amount"]

        if not final_result.get("due_date"):
            final_result["due_date"] = fallback["due_date"]

        if not final_result.get("category"):
            final_result["category"] = "Bills"

        if not final_result.get("confidence"):
            final_result["confidence"] = 0.70

        return final_result

    except Exception as error:
        fallback["reason"] = f"AI provider bill extraction failed. Fallback used. Error: {str(error)}"
        return fallback


# Compatibility aliases for callers upgrading from the Gemini-only implementation.
analyze_receipt_ocr_with_gemini = analyze_receipt_ocr
analyze_bill_ocr_with_gemini = analyze_bill_ocr
