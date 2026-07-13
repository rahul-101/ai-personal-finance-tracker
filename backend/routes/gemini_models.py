import os
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
from google import genai

load_dotenv()

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


@router.get("/ai/models")
def list_gemini_models():
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing in .env"
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        available_models = []

        for model in client.models.list():
            supported_actions = getattr(model, "supported_actions", [])

            available_models.append(
                {
                    "name": model.name,
                    "display_name": getattr(model, "display_name", ""),
                    "supported_actions": supported_actions
                }
            )

        generate_content_models = []

        for item in available_models:
            if "generateContent" in item.get("supported_actions", []):
                generate_content_models.append(item)

        return {
            "status": "success",
            "generate_content_models": generate_content_models,
            "all_models": available_models
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Gemini models: {str(error)}"
        )
