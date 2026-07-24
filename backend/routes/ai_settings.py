import json
from datetime import datetime, timedelta, timezone

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


def build_rule_based_weekly_digest(summary: dict) -> dict:
    """Provide useful local guidance when an AI provider is unavailable."""
    income = float(summary["income"])
    expenses = float(summary["expenses"])
    net_cash_flow = float(summary["net_cash_flow"])
    categories = summary.get("category_summary", {})
    top_category = max(categories, key=categories.get) if categories else None
    insights = []
    if income <= 0 and expenses <= 0:
        insights.append("No income or expense activity was recorded in the last seven days. Add or sync transactions for a more useful digest.")
    elif net_cash_flow < 0:
        insights.append("Recorded outflows exceeded income and refunds this week. Review discretionary spending before the next billing cycle.")
    else:
        insights.append("Your recorded cash flow was positive this week. Consider moving part of the surplus toward your savings or investment goal.")
    if top_category:
        insights.append(f"{top_category} was the largest recorded expense category this week. Check whether its spending aligns with your plan.")
    return {
        "headline": "Your weekly finance snapshot",
        "insights": insights[:3],
        "disclaimer": "Educational information based on recorded aggregate data; not financial advice.",
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


@router.post("/ai/weekly-digest")
def generate_weekly_digest():
    """Generate concise AI guidance from the most recent seven calendar days."""
    configuration = get_ai_configuration()
    if not is_ai_configured():
        raise HTTPException(status_code=400, detail="The selected AI provider is not configured")

    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=6)
    summary_result = dashboard_summary(date_from=week_start, date_to=today)
    if summary_result.get("status") != "success":
        raise HTTPException(status_code=500, detail="Unable to load weekly finance data")

    summary = summary_result["summary"]
    safe_summary = {
        "period": {"from": week_start.isoformat(), "to": today.isoformat()},
        "income": summary.get("total_income", summary["total_credit"]),
        "expenses": summary.get("total_expenses", summary["total_spend"]),
        "refunds": summary.get("total_refunds", 0),
        "investments": summary.get("total_investments", 0),
        "transfers": summary.get("total_transfers", 0),
        "net_cash_flow": summary.get("net_cash_flow", summary["net_balance"]),
        "transaction_count": summary["total_transactions"],
        "category_summary": summary["category_summary"],
        "top_merchants": summary["top_merchants"][:5],
        "profile_preferences": get_profile_ai_preferences(),
    }
    prompt = (
        "You are a helpful personal-finance coach. Analyze only this seven-day aggregate data. "
        "Do not invent facts, make guarantees, give investment advice, or mention specific providers. "
        "Return exactly valid JSON with this schema: "
        '{"headline":"short string","insights":["actionable string"],'
        '"disclaimer":"short educational disclaimer"}. Keep insights to a maximum of three.\n\n'
        f"Data: {json.dumps(safe_summary)}"
    )
    digest_source = "ai"
    try:
        response = parse_provider_json(generate_text(prompt))
        headline = response.get("headline")
        insights = [item for item in response.get("insights", []) if isinstance(item, str) and item.strip()][:3]
        disclaimer = response.get("disclaimer")
        if not isinstance(headline, str) or not insights or not isinstance(disclaimer, str):
            raise ValueError("The provider returned an unexpected digest format")
        insight = {"headline": headline.strip(), "insights": insights, "disclaimer": disclaimer.strip()}
    except (AIProviderError, ValueError, json.JSONDecodeError):
        digest_source = "rule_based"
        insight = build_rule_based_weekly_digest(safe_summary)
    try:
        ai_insights_collection.insert_one(
            {**insight, "kind": "weekly_digest", "source": digest_source, "provider": configuration.provider, "model": configuration.model, "created_at": datetime.now(timezone.utc)}
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to save weekly digest: {error}")
    return {"status": "success", "provider": configuration.provider, "model": configuration.model, "source": digest_source, "period": safe_summary["period"], "insight": insight}
