import os
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from database import gmail_tokens_collection, oauth_states_collection
from security import encrypt_text, decrypt_text

load_dotenv()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = os.getenv("OAUTHLIB_INSECURE_TRANSPORT", "0")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

GMAIL_SCOPES_TEXT = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.readonly"
)

GMAIL_SCOPES = [scope.strip() for scope in GMAIL_SCOPES_TEXT.split(",")]

DEMO_USER_ID = "demo-user"

router = APIRouter()
logger = logging.getLogger(__name__)


def create_google_flow(state: str | None = None):
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID is missing in .env file.")

    if not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_SECRET is missing in .env file.")

    if not GOOGLE_REDIRECT_URI:
        raise ValueError("GOOGLE_REDIRECT_URI is missing in .env file.")

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=False,
        state=state,
    )

    return flow


def create_authorization_url() -> str:
    """Create a one-time OAuth state value and persist it before redirecting."""
    flow = create_google_flow(state=secrets.token_urlsafe(32))
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    oauth_states_collection.insert_one(
        {
            "state": state,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
    )
    return authorization_url


@router.get("/auth/google")
def google_login():
    try:
        return RedirectResponse(create_authorization_url())

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Google authorization URL: {str(error)}"
        )


@router.get("/auth/google/url")
def google_login_url():
    try:
        return {
            "status": "success",
            "authorization_url": create_authorization_url()
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Google authorization URL: {str(error)}"
        )


@router.get("/auth/google/callback")
def google_callback(code: str, state: str):
    try:
        state_document = oauth_states_collection.find_one_and_delete(
            {
                "state": state,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            }
        )
        if not state_document:
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

        flow = create_google_flow(state=state)

        flow.fetch_token(code=code)

        credentials = flow.credentials

        token_json = credentials.to_json()

        encrypted_token = encrypt_text(token_json)

        gmail_tokens_collection.update_one(
            {
                "user_id": DEMO_USER_ID,
                "provider": "gmail"
            },
            {
                "$set": {
                    "user_id": DEMO_USER_ID,
                    "provider": "gmail",
                    "encrypted_token_json": encrypted_token,
                    "scopes": GMAIL_SCOPES,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        return {
            "status": "success",
            "message": "Gmail connected successfully. Token stored securely in MongoDB."
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(
            status_code=500,
            detail="Google OAuth callback failed"
        )


@router.get("/gmail/status")
def gmail_status():
    token_doc = gmail_tokens_collection.find_one(
        {
            "user_id": DEMO_USER_ID,
            "provider": "gmail"
        }
    )

    if token_doc:
        return {
            "connected": True,
            "message": "Gmail is connected"
        }

    return {
        "connected": False,
        "message": "Gmail is not connected"
    }


def save_refreshed_credentials(credentials):
    token_json = credentials.to_json()
    encrypted_token = encrypt_text(token_json)

    gmail_tokens_collection.update_one(
        {
            "user_id": DEMO_USER_ID,
            "provider": "gmail"
        },
        {
            "$set": {
                "encrypted_token_json": encrypted_token,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )


def load_gmail_credentials():
    token_doc = gmail_tokens_collection.find_one(
        {
            "user_id": DEMO_USER_ID,
            "provider": "gmail"
        }
    )

    if not token_doc:
        return None

    encrypted_token = token_doc.get("encrypted_token_json")

    if not encrypted_token:
        return None

    token_json = decrypt_text(encrypted_token)

    token_info = json.loads(token_json)

    credentials = Credentials.from_authorized_user_info(
        token_info,
        scopes=GMAIL_SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_refreshed_credentials(credentials)

    return credentials


@router.get("/gmail/profile")
def gmail_profile():
    try:
        credentials = load_gmail_credentials()

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Gmail is not connected. Open /auth/google first."
            )

        gmail_service = build("gmail", "v1", credentials=credentials)

        profile = gmail_service.users().getProfile(userId="me").execute()

        return {
            "status": "success",
            "profile": profile
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Gmail profile: {str(error)}"
        )


@router.post("/gmail/disconnect")
def gmail_disconnect():
    result = gmail_tokens_collection.delete_one(
        {
            "user_id": DEMO_USER_ID,
            "provider": "gmail"
        }
    )

    return {
        "status": "success",
        "message": "Gmail disconnected successfully",
        "deleted_count": result.deleted_count
    }
