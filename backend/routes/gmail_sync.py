import base64
from datetime import datetime

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build

from database import transactions_collection
from database import gmail_logs_collection
from routes.gmail_auth import load_gmail_credentials
from services.email_parser import parse_transaction_email
from services.email_parser import mask_sensitive_numbers
from services.email_parser import normalize_text
from services.ai_analysis import analyze_transaction_email


router = APIRouter()


def get_header(headers, header_name):
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")

    return ""


def decode_base64_urlsafe(data):
    if not data:
        return ""

    try:
        byte_data = data.encode("UTF-8")
        decoded_bytes = base64.urlsafe_b64decode(byte_data)
        return decoded_bytes.decode("UTF-8", errors="ignore")
    except Exception:
        return ""


def extract_body_from_payload(payload):
    body_text = ""

    if not payload:
        return body_text

    body = payload.get("body", {})
    body_data = body.get("data")

    if body_data:
        body_text = body_text + " " + decode_base64_urlsafe(body_data)

    parts = payload.get("parts", [])

    for part in parts:
        mime_type = part.get("mimeType", "")

        if mime_type in ["text/plain", "text/html"]:
            part_body = part.get("body", {})
            part_data = part_body.get("data")

            if part_data:
                body_text = body_text + " " + decode_base64_urlsafe(part_data)

        nested_parts = part.get("parts", [])

        for nested_part in nested_parts:
            nested_body = nested_part.get("body", {})
            nested_data = nested_body.get("data")

            if nested_data:
                body_text = body_text + " " + decode_base64_urlsafe(nested_data)

    return body_text


def get_gmail_service():
    credentials = load_gmail_credentials()

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Gmail is not connected. Open /auth/google first."
        )

    gmail_service = build("gmail", "v1", credentials=credentials)

    return gmail_service


@router.get("/gmail/messages")
def preview_gmail_messages(max_results: int = 10):
    try:
        gmail_service = get_gmail_service()

        query = 'newer_than:30d (debited OR credited OR "card used" OR "payment successful" ' \
        'OR "has been debited" OR "has been credited" OR "UPI" OR "ATM-WDL") -digest -newsletter -unsubscribe -"loan offer" -"credit card offer" -"market update" -"commercial papers"'

        response = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = response.get("messages", [])

        preview_list = []

        for message in messages:
            message_id = message.get("id")

            full_message = gmail_service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            payload = full_message.get("payload", {})
            headers = payload.get("headers", [])

            sender = get_header(headers, "From")
            subject = get_header(headers, "Subject")
            date_header = get_header(headers, "Date")
            snippet = full_message.get("snippet", "")

            preview_list.append(
                {
                    "gmail_message_id": message_id,
                    "from": sender,
                    "subject": subject,
                    "date": date_header,
                    "snippet": snippet
                }
            )

        return {
            "status": "success",
            "count": len(preview_list),
            "messages": preview_list
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Gmail messages: {str(error)}"
        )


@router.post("/gmail/sync")
def sync_gmail_transactions(max_results: int = 20):
    try:
        gmail_service = get_gmail_service()

        query = 'newer_than:30d (debited OR credited OR "card used" OR "payment successful" ' \
        'OR "has been debited" OR "has been credited" OR "UPI" OR "ATM-WDL") -digest -newsletter -unsubscribe -"loan offer" -"credit card offer" -"market update" -"commercial papers"'

        response = gmail_service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = response.get("messages", [])

        summary = {
            "total_fetched": len(messages),
            "inserted_transactions": 0,
            "ignored_emails": 0,
            "duplicate_emails": 0,
            "review_required": 0,
            "failed_emails": 0
        }

        processed_details = []

        for message in messages:
            message_id = message.get("id")

            existing_log = gmail_logs_collection.find_one(
                {
                    "gmail_message_id": message_id
                }
            )

            if existing_log:
                summary["duplicate_emails"] = summary["duplicate_emails"] + 1

                processed_details.append(
                    {
                        "gmail_message_id": message_id,
                        "status": "duplicate_skipped"
                    }
                )

                continue

            try:
                full_message = gmail_service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format="full"
                ).execute()

                payload = full_message.get("payload", {})
                headers = payload.get("headers", [])

                sender = get_header(headers, "From")
                subject = get_header(headers, "Subject")
                date_header = get_header(headers, "Date")
                body = extract_body_from_payload(payload)

                rule_based_result = parse_transaction_email(
                    subject=subject,
                    body=body,
                    sender=sender,
                    gmail_message_id=message_id
                )

                if not rule_based_result.get("is_transaction"):
                    gmail_logs_collection.insert_one(
                        {
                            "gmail_message_id": message_id,
                            "from": sender,
                            "subject": subject,
                            "status": rule_based_result.get("ignore_reason"),
                            "created_at": datetime.utcnow()
                        }
                    )

                    summary["ignored_emails"] = summary["ignored_emails"] + 1

                    processed_details.append(
                        {
                            "gmail_message_id": message_id,
                            "subject": subject,
                            "status": rule_based_result.get("ignore_reason")
                        }
                    )

                    continue

                combined_text = normalize_text(subject + " " + body)
                masked_email_text = mask_sensitive_numbers(combined_text)

                ai_result = analyze_transaction_email(
                    subject=subject,
                    sender=sender,
                    masked_email_text=masked_email_text,
                    rule_based_data=rule_based_result
                )

                if not ai_result.get("is_transaction"):
                    gmail_logs_collection.insert_one(
                        {
                            "gmail_message_id": message_id,
                            "from": sender,
                            "subject": subject,
                            "status": "gemini_rejected",
                            "reason": ai_result.get("ignore_reason", "Gemini marked as non-transaction"),
                            "created_at": datetime.utcnow()
                        }
                    )

                    summary["ignored_emails"] = summary["ignored_emails"] + 1

                    processed_details.append(
                        {
                            "gmail_message_id": message_id,
                            "subject": subject,
                            "status": "gemini_rejected",
                            "reason": ai_result.get("ignore_reason")
                        }
                    )

                    continue

                confidence = float(ai_result.get("confidence", 0.70))

                status = "confirmed"

                
                if confidence < 0.75:
                    gmail_logs_collection.insert_one(
                        {
                            "gmail_message_id": message_id,
                            "from": sender,
                            "subject": subject,
                            "status": "review_required_not_inserted",
                            "reason": ai_result.get("reason", "Low AI confidence"),
                            "ai_confidence": confidence,
                            "created_at": datetime.utcnow()
                        }
                    )

                    summary["review_required"] = summary["review_required"] + 1

                    processed_details.append(
                        {
                            "gmail_message_id": message_id,
                            "subject": subject,
                            "status": "review_required_not_inserted",
                            "reason": ai_result.get("reason", "Low AI confidence"),
                            "ai_confidence": confidence
                        }
                    )

                    continue


                transaction_data = {
                    "date": ai_result.get("date") or rule_based_result.get("date"),
                    "merchant": ai_result.get("merchant") or rule_based_result.get("merchant"),
                    "amount": float(ai_result.get("amount") or rule_based_result.get("amount")),
                    "category": ai_result.get("category") or rule_based_result.get("category"),
                    "source": "email",
                    "transaction_type": ai_result.get("transaction_type") or rule_based_result.get("transaction_type"),
                    "payment_mode": ai_result.get("payment_mode", "unknown"),
                    "masked_account": ai_result.get("masked_account", ""),
                    "email_sender": sender,
                    "gmail_message_id": message_id,
                    "masked_evidence": masked_email_text[:500],
                    "ai_confidence": confidence,
                    "ai_reason": ai_result.get("reason", ""),
                    "status": status,
                    "created_at": datetime.utcnow()
                }

                insert_result = transactions_collection.insert_one(transaction_data)

                gmail_logs_collection.insert_one(
                    {
                        "gmail_message_id": message_id,
                        "from": sender,
                        "subject": subject,
                        "status": "transaction_inserted",
                        "transaction_id": str(insert_result.inserted_id),
                        "ai_confidence": confidence,
                        "created_at": datetime.utcnow()
                    }
                )

                summary["inserted_transactions"] = summary["inserted_transactions"] + 1

                processed_details.append(
                    {
                        "gmail_message_id": message_id,
                        "subject": subject,
                        "status": "transaction_inserted",
                        "transaction_id": str(insert_result.inserted_id),
                        "merchant": transaction_data["merchant"],
                        "amount": transaction_data["amount"],
                        "category": transaction_data["category"],
                        "ai_confidence": confidence,
                        "review_status": status
                    }
                )

            except Exception as email_error:
                gmail_logs_collection.insert_one(
                    {
                        "gmail_message_id": message_id,
                        "status": "processing_failed",
                        "error": str(email_error),
                        "created_at": datetime.utcnow()
                    }
                )

                summary["failed_emails"] = summary["failed_emails"] + 1

                processed_details.append(
                    {
                        "gmail_message_id": message_id,
                        "status": "processing_failed",
                        "error": str(email_error)
                    }
                )

        return {
            "status": "success",
            "summary": summary,
            "details": processed_details
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Gmail sync failed: {str(error)}"
        )
