import unittest

from services.email_parser import mask_sensitive_numbers, parse_transaction_email


class EmailParserTests(unittest.TestCase):
    def test_detects_a_debit_transaction(self):
        result = parse_transaction_email(
            subject="Transaction alert",
            body="Your account was debited by INR 849.00 at SWIGGY on 2026-07-02.",
            sender="alerts@bank.example",
            gmail_message_id="message-1",
        )

        self.assertTrue(result["is_transaction"])
        self.assertEqual(result["amount"], 849.00)
        self.assertEqual(result["category"], "Food")

    def test_ignores_an_otp(self):
        result = parse_transaction_email(
            subject="Your OTP",
            body="Your OTP is 123456 for payment of INR 849.",
            sender="alerts@bank.example",
            gmail_message_id="message-2",
        )

        self.assertFalse(result["is_transaction"])
        self.assertEqual(result["ignore_reason"], "ignored_security_or_otp")

    def test_masks_long_card_numbers(self):
        masked = mask_sensitive_numbers("Card 1234 5678 9012 3456 was used")

        self.assertEqual(masked, "Card XXXXXXXXXXXX3456 was used")
