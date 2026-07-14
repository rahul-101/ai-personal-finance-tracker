from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image, UnidentifiedImageError

from database import transactions_collection
from database import receipts_collection
from database import bills_collection

from services.ocr_parser import extract_text_from_image
from services.ocr_parser import extract_amount_from_text
from services.ocr_parser import extract_merchant_from_receipt
from services.ocr_parser import extract_due_date
from services.ocr_parser import extract_provider_from_bill

from services.ai_ocr import analyze_receipt_ocr
from services.ai_ocr import analyze_bill_ocr


router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def read_validated_image(file: UploadFile) -> bytes:
    """Read a small, decodable image before handing it to OCR or an AI provider."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPEG, PNG, and WebP images are supported",
        )

    image_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    return image_bytes


@router.post("/receipts/upload")
def upload_receipt(file: UploadFile = File(...)):
    try:
        image_bytes = read_validated_image(file)

        ocr_text = extract_text_from_image(image_bytes)

        fallback_amount = extract_amount_from_text(ocr_text)

        fallback_merchant = extract_merchant_from_receipt(ocr_text)

        ai_result = analyze_receipt_ocr(
            ocr_text=ocr_text,
            fallback_merchant=fallback_merchant,
            fallback_amount=fallback_amount
        )

        is_valid_receipt = ai_result.get("is_valid_receipt", True)

        amount = float(ai_result.get("amount") or 0)

        merchant = ai_result.get("merchant") or fallback_merchant or "Unknown Receipt Merchant"

        confidence = float(ai_result.get("confidence") or 0.65)

        if not is_valid_receipt:
            status = "rejected_not_receipt"
        elif amount <= 0:
            status = "review_required"
        elif confidence < 0.75:
            status = "review_required"
        else:
            status = "confirmed"

        transaction_id = None

        if is_valid_receipt:
            transaction_data = {
                "date": ai_result.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                "merchant": merchant,
                "amount": amount,
                "category": ai_result.get("category", "Others"),
                "source": "receipt",
                "transaction_type": "debit",
                "payment_mode": ai_result.get("payment_mode", "unknown"),
                "status": status,
                "masked_evidence": ocr_text[:500],
                "ai_confidence": confidence,
                "ai_reason": ai_result.get("reason", ""),
                "created_at": datetime.utcnow()
            }

            insert_result = transactions_collection.insert_one(transaction_data)
            transaction_id = str(insert_result.inserted_id)

        receipt_data = {
            "transaction_id": transaction_id,
            "file_name": file.filename,
            "ocr_text": ocr_text[:3000],
            "raw_image_stored": False,
            "ai_result": ai_result,
            "status": status,
            "created_at": datetime.utcnow()
        }

        receipts_collection.insert_one(receipt_data)

        return {
            "status": "success",
            "message": "Receipt processed successfully with AI enhancement",
            "transaction_id": transaction_id,
            "merchant": merchant,
            "amount": amount,
            "category": ai_result.get("category", "Others"),
            "payment_mode": ai_result.get("payment_mode", "unknown"),
            "review_status": status,
            "ai_confidence": confidence,
            "ai_reason": ai_result.get("reason", ""),
            "ocr_preview": ocr_text[:500]
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Receipt upload failed: {str(error)}"
        )


@router.post("/bills/upload")
def upload_bill(file: UploadFile = File(...)):
    try:
        image_bytes = read_validated_image(file)

        ocr_text = extract_text_from_image(image_bytes)

        fallback_amount = extract_amount_from_text(ocr_text)

        fallback_provider = extract_provider_from_bill(ocr_text)

        fallback_due_date = extract_due_date(ocr_text)

        ai_result = analyze_bill_ocr(
            ocr_text=ocr_text,
            fallback_provider=fallback_provider,
            fallback_amount=fallback_amount,
            fallback_due_date=fallback_due_date
        )

        is_valid_bill = ai_result.get("is_valid_bill", True)

        amount = float(ai_result.get("amount") or 0)

        provider = ai_result.get("provider") or fallback_provider or "Unknown Bill Provider"

        confidence = float(ai_result.get("confidence") or 0.65)

        if not is_valid_bill:
            status = "rejected_not_bill"
        elif amount <= 0:
            status = "review_required"
        elif confidence < 0.75:
            status = "review_required"
        else:
            status = "uploaded"

        bill_data = {
            "provider": provider,
            "bill_type": ai_result.get("bill_type", "Bill"),
            "amount": amount,
            "currency": ai_result.get("currency", "INR"),
            "bill_date": ai_result.get("bill_date", ""),
            "due_date": ai_result.get("due_date", fallback_due_date or ""),
            "category": ai_result.get("category", "Bills"),
            "status": status,
            "source": "bill_upload",
            "file_name": file.filename,
            "ocr_text": ocr_text[:3000],
            "raw_file_stored": False,
            "ai_confidence": confidence,
            "ai_reason": ai_result.get("reason", ""),
            "ai_result": ai_result,
            "created_at": datetime.utcnow()
        }

        insert_result = bills_collection.insert_one(bill_data)

        return {
            "status": "success",
            "message": "Bill processed successfully with AI enhancement",
            "bill_id": str(insert_result.inserted_id),
            "provider": provider,
            "bill_type": ai_result.get("bill_type", "Bill"),
            "amount": amount,
            "due_date": ai_result.get("due_date", fallback_due_date or ""),
            "review_status": status,
            "ai_confidence": confidence,
            "ai_reason": ai_result.get("reason", ""),
            "ocr_preview": ocr_text[:500]
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Bill upload failed: {str(error)}"
        )


@router.get("/bills")
def get_bills():
    try:
        bills = list(
            bills_collection.find()
            .sort("created_at", -1)
            .limit(50)
        )

        formatted_bills = []

        for bill in bills:
            bill["_id"] = str(bill["_id"])

            if "created_at" in bill:
                bill["created_at"] = bill["created_at"].isoformat()

            formatted_bills.append(bill)

        return {
            "status": "success",
            "count": len(formatted_bills),
            "bills": formatted_bills
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch bills: {str(error)}"
        )


@router.get("/receipts")
def get_receipts():
    try:
        receipts = list(
            receipts_collection.find()
            .sort("created_at", -1)
            .limit(50)
        )

        formatted_receipts = []

        for receipt in receipts:
            receipt["_id"] = str(receipt["_id"])

            if "created_at" in receipt:
                receipt["created_at"] = receipt["created_at"].isoformat()

            formatted_receipts.append(receipt)

        return {
            "status": "success",
            "count": len(formatted_receipts),
            "receipts": formatted_receipts
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch receipts: {str(error)}"
        )
