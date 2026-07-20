import os
from typing import Final

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

MONGO_URI: Final[str | None] = os.getenv("MONGO_URI")
DATABASE_NAME: Final[str] = os.getenv("DATABASE_NAME", "finance_tracker")

if not MONGO_URI:
    raise ValueError("MONGO_URI is missing. Please add it in backend/.env file.")

# ``connect=False`` keeps importing the FastAPI application side-effect free.
# MongoDB is contacted when an endpoint actually performs a database operation.
client = MongoClient(
    MONGO_URI,
    server_api=ServerApi("1"),
    connect=False,
    serverSelectionTimeoutMS=5_000,
)

db = client[DATABASE_NAME]

transactions_collection = db["transactions"]

gmail_tokens_collection = db["gmail_tokens"]

gmail_logs_collection = db["gmail_logs"]

gmail_sync_runs_collection = db["gmail_sync_runs"]

oauth_states_collection = db["oauth_states"]

receipts_collection = db["receipts"]

bills_collection = db["bills"]

ai_insights_collection = db["ai_insights"]

budgets_collection = db["budgets"]

profile_collection = db["profile"]


def check_mongodb_connection():
    try:
        client.admin.command("ping")
        return True
    except Exception as error:
        print("MongoDB connection error:", error)
        return False


def create_database_indexes() -> None:
    """Create the indexes that support the application's current query patterns."""
    transactions_collection.create_index([("created_at", -1)])
    transactions_collection.create_index([("date", -1)])
    transactions_collection.create_index(
        [("gmail_message_id", 1)],
        unique=True,
        sparse=True,
        name="unique_gmail_transaction",
    )

    gmail_tokens_collection.create_index(
        [("user_id", 1), ("provider", 1)],
        unique=True,
        name="unique_user_provider_token",
    )
    gmail_logs_collection.create_index(
        [("gmail_message_id", 1)],
        unique=True,
        name="unique_gmail_log",
    )
    gmail_logs_collection.create_index([("created_at", -1)])
    gmail_sync_runs_collection.create_index([("created_at", -1)])
    oauth_states_collection.create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0,
        name="expire_oauth_state",
    )
    receipts_collection.create_index([("created_at", -1)])
    bills_collection.create_index([("created_at", -1)])
    ai_insights_collection.create_index([("created_at", -1)])
    # Replace the first single-budget index with one budget document per month.
    try:
        budgets_collection.drop_index("unique_budget_scope")
    except Exception:
        pass
    budgets_collection.create_index([("scope", 1), ("month", 1)], unique=True, name="unique_budget_month")
    profile_collection.create_index([("scope", 1)], unique=True, name="unique_profile_scope")
