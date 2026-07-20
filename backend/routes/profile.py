from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from database import profile_collection
from models import PersonalProfile


router = APIRouter()
PROFILE_SCOPE = "single_user"


def serialize_profile(document: dict) -> dict:
    profile = {key: value for key, value in document.items() if key not in {"_id", "scope"}}
    for field, value in profile.items():
        if isinstance(value, datetime):
            profile[field] = value.isoformat()
    return profile


@router.get("/profile")
def get_profile():
    try:
        profile = profile_collection.find_one({"scope": PROFILE_SCOPE})
        return {"status": "success", "profile": serialize_profile(profile) if profile else None}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load profile: {error}")


@router.put("/profile")
def save_profile(profile: PersonalProfile):
    try:
        now = datetime.now(timezone.utc)
        profile_collection.update_one(
            {"scope": PROFILE_SCOPE},
            {"$set": {**profile.model_dump(mode="json"), "updated_at": now}, "$setOnInsert": {"scope": PROFILE_SCOPE, "created_at": now}},
            upsert=True,
        )
        saved_profile = profile_collection.find_one({"scope": PROFILE_SCOPE})
        return {"status": "success", "message": "Profile saved", "profile": serialize_profile(saved_profile)}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to save profile: {error}")
