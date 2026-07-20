import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from database import ai_insights_collection, profile_collection
from services.ai_client import AIProviderError, generate_text, get_ai_configuration, is_ai_configured
from routes.budgets import build_budget_response
from routes.dashboard import dashboard_summary

router = APIRouter()


def parse_provider_json(response_text: str) -> dict:
    """Accept JSON responses wrapped in a Markdown code fence by some providers."""
    cleaned_response = response_text.strip()
    if cleaned_response.startswith("```"):
        lines = cleaned_response.splitlines()
        cleaned_response = "\n".join(lines[1:-1]).strip()

    return json.loads(cleaned_response)


def get_profile_ai_preferences() -> dict:
    """Return only goal-oriented preferences suitable for an AI finance prompt."""
    profile = profile_collection.find_one({"scope": "single_user"})
    if not profile:
        return {}
    return {
        "currency": profile.get("currency", "INR"),
        "monthly_income_target": profile.get("monthly_income_target"),
        "savings_goal": profile.get("savings_goal"),
        "investment_goal": profile.get("investment_goal"),
        "priorities": profile.get("priorities", []),
    }


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


@router.get("/ai/insights/history")
def get_finance_insight_history(limit: int = 5):
    """Return recent saved AI insights without re-contacting a provider."""
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20")

    try:
        documents = list(ai_insights_collection.find().sort("created_at", -1).limit(limit))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load insight history: {error}")

    insights = [
        {
            "_id": str(document["_id"]),
            "headline": document["headline"],
            "insights": document["insights"],
            "disclaimer": document["disclaimer"],
            "provider": document["provider"],
            "model": document["model"],
            "created_at": document["created_at"].isoformat(),
        }
        for document in documents
    ]
    return {"status": "success", "insights": insights}


@router.post("/ai/insights")
def generate_finance_insights():
    """Generate concise advice from aggregate dashboard figures only."""
    configuration = get_ai_configuration()
    if not is_ai_configured():
        raise HTTPException(status_code=400, detail="The selected AI provider is not configured")

    summary_result = dashboard_summary()
    if summary_result.get("status") != "success":
        raise HTTPException(status_code=500, detail="Unable to load dashboard data for insights")

    summary = summary_result["summary"]
    try:
        budget_result = build_budget_response()
        safe_budget = {
            "month": budget_result["month"],
            "overall": budget_result["overall"],
            "categories": budget_result["categories"],
        }
    except Exception:
        # Budget context improves advice but should never block insight generation.
        safe_budget = {"available": False}
    try:
        profile_preferences = get_profile_ai_preferences()
    except Exception:
        profile_preferences = {}
    safe_summary = {
        "total_spend": summary["total_spend"],
        "total_credit": summary["total_credit"],
        "net_balance": summary["net_balance"],
        "total_income": summary.get("total_income", summary["total_credit"]),
        "total_expenses": summary.get("total_expenses", summary["total_spend"]),
        "total_refunds": summary.get("total_refunds", 0),
        "total_investments": summary.get("total_investments", 0),
        "total_transfers": summary.get("total_transfers", 0),
        "total_transactions": summary["total_transactions"],
        "review_required_count": summary["review_required_count"],
        "review_log_count": summary["review_log_count"],
        "bills_due_count": summary["bills_due_count"],
        "category_summary": summary["category_summary"],
        "top_merchants": summary["top_merchants"][:5],
        "monthly_trend": summary["monthly_trend"][-6:],
        "budget": safe_budget,
        "profile_preferences": profile_preferences,
    }
    prompt = (
        "You are a helpful personal-finance coach. Analyze only this aggregate financial data. "
        "Do not invent facts, make guarantees, give investment advice, or mention specific providers. "
        "Return exactly valid JSON with this schema: "
        '{"headline":"short string","insights":["actionable string", "actionable string"],'
        '"disclaimer":"short educational disclaimer"}. Keep insights to a maximum of three.\n\n'
        f"Data: {json.dumps(safe_summary)}"
    )

    try:
        response_text = generate_text(prompt)
        response = parse_provider_json(response_text)
        headline = response.get("headline")
        insights = response.get("insights")
        disclaimer = response.get("disclaimer")
        if not isinstance(headline, str) or not isinstance(insights, list) or not isinstance(disclaimer, str):
            raise ValueError("The provider returned an unexpected insight format")
        insights = [item for item in insights if isinstance(item, str) and item.strip()][:3]
        if not insights:
            raise ValueError("The provider returned no usable insights")
    except (AIProviderError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail=f"Unable to generate insights: {error}")

    insight = {"headline": headline.strip(), "insights": insights, "disclaimer": disclaimer.strip()}
    try:
        ai_insights_collection.insert_one(
            {
                **insight,
                "provider": configuration.provider,
                "model": configuration.model,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to save insight history: {error}")

    return {
        "status": "success",
        "provider": configuration.provider,
        "model": configuration.model,
        "insight": insight,
    }
