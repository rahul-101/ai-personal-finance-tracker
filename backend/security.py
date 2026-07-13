import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise ValueError("FERNET_KEY is missing. Please add it in backend/.env file.")

fernet = Fernet(FERNET_KEY.encode())


def encrypt_text(plain_text: str) -> str:
    encrypted_value = fernet.encrypt(plain_text.encode())
    return encrypted_value.decode()


def decrypt_text(encrypted_text: str) -> str:
    decrypted_value = fernet.decrypt(encrypted_text.encode())
    return decrypted_value.decode()