import re
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter
import pytesseract


def preprocess_image(image_bytes: bytes):
    image = Image.open(BytesIO(image_bytes))

    image = image.convert("L")

    image = ImageOps.autocontrast(image)

    image = image.filter(ImageFilter.SHARPEN)

    return image


def extract_text_from_image(image_bytes: bytes) -> str:
    image = preprocess_image(image_bytes)

    extracted_text = pytesseract.image_to_string(image)

    return extracted_text.strip()


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = re.sub(" +", " ", text)

    return text.strip()


def extract_amount_from_text(text: str):
    cleaned_text = normalize_text(text)

    priority_patterns = [
        r"(?:grand total|total amount|amount due|total|net amount)\D+([0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
        r"(?:INR|Rs\.?|₹)\s*([0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)"
    ]

    for pattern in priority_patterns:
        match = re.search(pattern, cleaned_text, re.IGNORECASE)

        if match:
            amount_text = match.group(1).replace(",", "")
            return float(amount_text)

    all_amounts = re.findall(r"\b[0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{2})\b", cleaned_text)

    numeric_amounts = []

    for amount in all_amounts:
        try:
            numeric_amounts.append(float(amount.replace(",", "")))
        except Exception:
            pass

    if numeric_amounts:
        return max(numeric_amounts)

    return None


def extract_merchant_from_receipt(text: str) -> str:
    if not text:
        return "Unknown Receipt Merchant"

    lines = text.splitlines()

    clean_lines = []

    for line in lines:
        clean_line = line.strip()

        if clean_line:
            clean_lines.append(clean_line)

    if len(clean_lines) > 0:
        first_line = clean_lines[0]

        if len(first_line) <= 80:
            return first_line.title()

    return "Unknown Receipt Merchant"


def extract_due_date(text: str):
    cleaned_text = normalize_text(text)

    patterns = [
        r"due date\D+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"pay by\D+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"last date\D+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned_text, re.IGNORECASE)

        if match:
            return match.group(1)

    return None


def extract_provider_from_bill(text: str) -> str:
    if not text:
        return "Unknown Bill Provider"

    lower_text = text.lower()

    known_providers = {
        "cesc": "CESC",
        "airtel": "Airtel",
        "jio": "Jio",
        "bsnl": "BSNL",
        "vodafone": "Vodafone",
        "vi": "Vi",
        "electricity": "Electricity Provider",
        "broadband": "Broadband Provider"
    }

    for keyword, provider in known_providers.items():
        if keyword in lower_text:
            return provider

    return extract_merchant_from_receipt(text)