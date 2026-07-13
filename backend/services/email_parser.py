import re
from datetime import datetime, timezone


SECURITY_KEYWORDS = [
    "otp",
    "one time password",
    "verification code",
    "login code",
    "do not share",
    "reset your password",
    "password reset"
]


MARKETING_KEYWORDS = [
    "offer",
    "loan offer",
    "pre-approved",
    "pre approved",
    "cashback offer",
    "limited period",
    "sale",
    "discount",
    "advertisement",
    "newsletter",
    "unsubscribe",
    "apply now",
    "credit card offer",
    "personal loan",
    "digest",
    "market update",
    "daily update",
    "weekly update",
    "breaking news",
    "top stories",
    "recommended for you",
    "read more"
]


NEWSLETTER_SUBJECT_KEYWORDS = [
    "digest",
    "newsletter",
    "market update",
    "stock market",
    "govt approves",
    "government approves",
    "commercial papers",
    "greenfield highway",
    "avenue supermarts",
    "groww digest",
    "morning brief",
    "evening brief",
    "business news",
    "market news",
    "top news"
]


TRANSACTION_KEYWORDS = [
    "debited",
    "credited",
    "spent",
    "paid",
    "purchase",
    "transaction",
    "withdrawn",
    "upi",
    "imps",
    "neft",
    "rtgs",
    "card used",
    "payment successful",
    "invoice",
    "bill paid",
    "refund",
    "was debited",
    "has been debited",
    "has been credited",
    "a/c no",
    "account no",
    "acct no",
    "available balance",
    "atm-wdl",
    "atm withdrawal"
]


STRONG_TRANSACTION_PATTERNS = [
    r"\bdebited\b",
    r"\bcredited\b",
    r"\bspent\b",
    r"\bpaid\b",
    r"\bwithdrawn\b",
    r"\bpayment successful\b",
    r"\bcard used\b",
    r"\bupi\b",
    r"\bimps\b",
    r"\bneft\b",
    r"\brtgs\b",
    r"\batm-wdl\b",
    r"\bavailable balance\b",
    r"\ba/c no\b",
    r"\baccount no\b",
    r"\bacct no\b"
]


CATEGORY_KEYWORDS = {
    "Cash Withdrawal": [
        "atm-wdl",
        "atm withdrawal",
        "cash withdrawal"
    ],
    "Food": [
        "swiggy",
        "zomato",
        "restaurant",
        "cafe",
        "pizza",
        "food"
    ],
    "Shopping": [
        "amazon",
        "flipkart",
        "myntra",
        "shopping",
        "store"
    ],
    "Transport": [
        "uber",
        "ola",
        "metro",
        "fuel",
        "petrol",
        "cab"
    ],
    "Bills": [
        "electricity",
        "bill",
        "broadband",
        "airtel",
        "jio",
        "recharge"
    ],
    "Groceries": [
        "grocery",
        "bigbasket",
        "blinkit",
        "dmart",
        "mart"
    ],
    "Entertainment": [
        "netflix",
        "prime",
        "spotify",
        "movie",
        "bookmyshow"
    ],
    "Health": [
        "pharmacy",
        "medicine",
        "hospital",
        "doctor"
    ]
}


def normalize_text(text: str) -> str:
    if not text:
        return ""

    cleaned_text = text.replace("\n", " ")
    cleaned_text = cleaned_text.replace("\r", " ")
    cleaned_text = re.sub(" +", " ", cleaned_text)

    return cleaned_text.strip()


def mask_sensitive_numbers(text: str) -> str:
    if not text:
        return ""

    def mask_match(match):
        value = match.group(0)
        digits = re.sub("[^0-9]", "", value)

        if len(digits) <= 4:
            return value

        return "X" * (len(digits) - 4) + digits[-4:]

    # Keep separators between digits, but do not consume whitespace after the
    # number. The final digit is matched separately for that reason.
    masked_text = re.sub(r"\b(?:\d[ -]?){7,18}\d\b", mask_match, text)

    return masked_text


def contains_any_keyword(text: str, keywords: list) -> bool:
    lower_text = text.lower()

    for keyword in keywords:
        if keyword in lower_text:
            return True

    return False


def is_newsletter_or_digest(subject: str, body: str) -> bool:
    subject_text = normalize_text(subject).lower()
    body_text = normalize_text(body).lower()
    combined_text = subject_text + " " + body_text

    if contains_any_keyword(subject_text, NEWSLETTER_SUBJECT_KEYWORDS):
        return True

    if "unsubscribe" in combined_text and contains_any_keyword(combined_text, MARKETING_KEYWORDS):
        return True

    if "groww digest" in combined_text:
        return True

    return False


def has_crore_lakh_news_amount(text: str) -> bool:
    lower_text = text.lower()

    patterns = [
        r"rs\.?\s*[0-9,]+(?:\.[0-9]+)?\s*cr\b",
        r"inr\s*[0-9,]+(?:\.[0-9]+)?\s*cr\b",
        r"₹\s*[0-9,]+(?:\.[0-9]+)?\s*cr\b",
        r"rs\.?\s*[0-9,]+(?:\.[0-9]+)?\s*crore\b",
        r"inr\s*[0-9,]+(?:\.[0-9]+)?\s*crore\b",
        r"₹\s*[0-9,]+(?:\.[0-9]+)?\s*crore\b",
        r"rs\.?\s*[0-9,]+(?:\.[0-9]+)?\s*lakh\b",
        r"inr\s*[0-9,]+(?:\.[0-9]+)?\s*lakh\b"
    ]

    for pattern in patterns:
        if re.search(pattern, lower_text):
            return True

    return False


def has_strong_transaction_pattern(text: str) -> bool:
    lower_text = text.lower()

    for pattern in STRONG_TRANSACTION_PATTERNS:
        if re.search(pattern, lower_text):
            return True

    return False


def extract_amount(text: str):
    if not text:
        return None

    if has_crore_lakh_news_amount(text):
        return None

    patterns = [
        r"(?:INR|Rs\.?|₹)\s*([0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
        r"([0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)\s*(?:INR|Rs\.?|₹)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            amount_text = match.group(1)
            amount_text = amount_text.replace(",", "")
            return float(amount_text)

    return None


def is_strong_otp_or_security_email(text: str) -> bool:
    lower_text = text.lower()

    otp_patterns = [
        "\\b[0-9]{4,8}\\b.*\\botp\\b",
        "\\botp\\b.*\\b[0-9]{4,8}\\b",
        "verification code",
        "login code",
        "reset your password",
        "password reset"
    ]

    for pattern in otp_patterns:
        if re.search(pattern, lower_text):
            return True

    return False


def should_ignore_email(subject: str, body: str) -> dict:
    combined_text = normalize_text(subject + " " + body)
    lower_text = combined_text.lower()

    if is_newsletter_or_digest(subject, body):
        return {
            "ignore": True,
            "reason": "ignored_newsletter_or_digest"
        }

    if has_crore_lakh_news_amount(combined_text):
        if not has_strong_transaction_pattern(combined_text):
            return {
                "ignore": True,
                "reason": "ignored_news_or_large_public_amount"
            }

    has_transaction_keyword = contains_any_keyword(lower_text, TRANSACTION_KEYWORDS)
    has_strong_pattern = has_strong_transaction_pattern(lower_text)
    amount = extract_amount(combined_text)
    has_amount = amount is not None

    if has_strong_pattern and has_amount:
        return {
            "ignore": False,
            "reason": "possible_transaction"
        }

    if is_strong_otp_or_security_email(lower_text):
        return {
            "ignore": True,
            "reason": "ignored_security_or_otp"
        }

    if contains_any_keyword(lower_text, MARKETING_KEYWORDS):
        return {
            "ignore": True,
            "reason": "ignored_marketing_or_offer"
        }

    if not has_transaction_keyword:
        return {
            "ignore": True,
            "reason": "ignored_no_transaction_keyword"
        }

    if not has_amount:
        return {
            "ignore": True,
            "reason": "ignored_no_amount"
        }

    if not has_strong_pattern:
        return {
            "ignore": True,
            "reason": "ignored_weak_transaction_signal"
        }

    return {
        "ignore": False,
        "reason": "possible_transaction"
    }


def extract_merchant(text: str) -> str:
    lower_text = text.lower()

    if "atm-wdl" in lower_text or "atm withdrawal" in lower_text:
        return "ATM Withdrawal"

    if "debited from your a/c" in lower_text or "debited from your account" in lower_text:
        if "atm" in lower_text:
            return "ATM Withdrawal"

        return "Bank Account Debit"

    patterns = [
        "at\\s+(ATM-[A-Za-z0-9/_-]{2,80})",
        "at\\s+([A-Za-z0-9 &._/-]{2,80})\\s+on",
        "at\\s+([A-Za-z0-9 &._/-]{2,80})\\.",
        "to\\s+([A-Za-z0-9 &._/-]{2,80})\\s+on",
        "merchant\\s*[:\\-]\\s*([A-Za-z0-9 &._/-]{2,80})"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            merchant = match.group(1)
            merchant = merchant.strip(" .,-")

            if merchant.lower().startswith("inr"):
                continue

            return merchant.title()

    return "Unknown"


def extract_transaction_type(text: str) -> str:
    lower_text = text.lower()

    if "credited" in lower_text or "refund" in lower_text or "received" in lower_text:
        return "credit"

    if "atm-wdl" in lower_text or "withdrawn" in lower_text:
        return "debit"

    return "debit"


def suggest_category(text: str) -> str:
    lower_text = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower_text:
                return category

    return "Others"


def parse_transaction_email(subject: str, body: str, sender: str, gmail_message_id: str) -> dict:
    clean_subject = normalize_text(subject)
    clean_body = normalize_text(body)
    combined_text = clean_subject + " " + clean_body

    ignore_result = should_ignore_email(clean_subject, clean_body)

    if ignore_result["ignore"]:
        return {
            "is_transaction": False,
            "ignore_reason": ignore_result["reason"]
        }

    masked_text = mask_sensitive_numbers(combined_text)

    amount = extract_amount(masked_text)

    merchant = extract_merchant(masked_text)

    category = suggest_category(masked_text)

    transaction_type = extract_transaction_type(masked_text)

    return {
        "is_transaction": True,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "merchant": merchant,
        "amount": amount,
        "category": category,
        "source": "email",
        "transaction_type": transaction_type,
        "email_sender": sender,
        "gmail_message_id": gmail_message_id,
        "masked_evidence": masked_text[:500]
    }
