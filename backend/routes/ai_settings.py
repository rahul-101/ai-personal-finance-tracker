from fastapi import APIRouter, HTTPException
from services.ai_client import AIProviderError, generate_text, get_ai_configuration, is_ai_configured

router = APIRouter()

@router.get("/ai/configuration")
def get_ai_configuration_status():
    """Expose non-secret provider metadata for the Settings screen."""
    configuration = get_ai_configuration()
    return {
        "status": "success",
        "provider": configuration.provider,
        "model": configuration.model,
        "configured": is_ai_configured(),
        "supported_providers": [
            "gemini",
            "openai",
            "anthropic",
            "groq",
            "mistral",
            "deepseek",
            "xai",
            "together",
        ],
    }


@router.post("/ai/test")
def test_ai_configuration():
    """Run a minimal real request without returning provider output to the browser."""
    configuration = get_ai_configuration()
    if not is_ai_configured():
        raise HTTPException(status_code=400, detail="The selected AI provider is not configured")

    try:
        generate_text('Return exactly this JSON object: {"status":"ok"}')
    except AIProviderError as error:
        raise HTTPException(status_code=503, detail=str(error))

    return {
        "status": "success",
        "message": "AI provider responded successfully",
        "provider": configuration.provider,
        "model": configuration.model,
    }
