"""Small in-process Gmail scheduler for the single-user local deployment."""
from datetime import datetime, timedelta, timezone

from database import profile_collection
from routes.gmail_sync import sync_gmail_transactions


CHECK_INTERVAL_SECONDS = 15 * 60
FREQUENCY_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


def run_due_gmail_sync(now: datetime | None = None) -> dict:
    """Run a scheduled sync when the saved profile frequency is due."""
    now = now or datetime.now(timezone.utc)
    profile = profile_collection.find_one({"scope": "single_user"}) or {}
    frequency = profile.get("gmail_sync_frequency", "manual")
    interval = FREQUENCY_INTERVALS.get(frequency)
    if not interval:
        return {"ran": False, "reason": "manual"}

    last_sync = profile.get("last_gmail_scheduled_sync_at")
    if isinstance(last_sync, datetime) and last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    if last_sync and now - last_sync < interval:
        return {"ran": False, "reason": "not_due"}

    try:
        result = sync_gmail_transactions(max_results=20, sync_source="scheduled")
        profile_collection.update_one(
            {"scope": "single_user"},
            {"$set": {"last_gmail_scheduled_sync_at": now, "last_gmail_scheduled_sync_status": "success"}},
        )
        return {"ran": True, "status": "success", "summary": result.get("summary", {})}
    except Exception as error:
        profile_collection.update_one(
            {"scope": "single_user"},
            {"$set": {"last_gmail_scheduled_sync_at": now, "last_gmail_scheduled_sync_status": "failed", "last_gmail_scheduled_sync_error": str(error)[:300]}},
        )
        return {"ran": True, "status": "failed"}
