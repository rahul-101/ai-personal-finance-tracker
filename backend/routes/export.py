import csv
import json
from io import StringIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId
from datetime import datetime

from database import transactions_collection


router = APIRouter()


def convert_value(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def convert_document(document):
    converted = {}

    for key, value in document.items():
        converted[key] = convert_value(value)

    return converted


@router.get("/export/json")
def export_transactions_json():
    try:
        transactions = list(
            transactions_collection.find()
            .sort("created_at", -1)
        )

        converted_transactions = [
            convert_document(tx) for tx in transactions
        ]

        json_data = json.dumps(
            converted_transactions,
            indent=2,
            ensure_ascii=False
        )

        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=transactions.json"
            }
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"JSON export failed: {str(error)}"
        )


@router.get("/export/csv")
def export_transactions_csv():
    try:
        transactions = list(
            transactions_collection.find()
            .sort("created_at", -1)
        )

        output = StringIO()

        fieldnames = [
            "date",
            "merchant",
            "amount",
            "category",
            "source",
            "transaction_type",
            "payment_mode",
            "status",
            "ai_confidence",
            "ai_reason",
            "gmail_message_id",
            "created_at"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()

        for tx in transactions:
            row = {}

            for field in fieldnames:
                value = tx.get(field, "")

                if isinstance(value, datetime):
                    value = value.isoformat()

                row[field] = value

            writer.writerow(row)

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=transactions.csv"
            }
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"CSV export failed: {str(error)}"
        )