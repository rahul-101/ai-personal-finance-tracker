"""Provider-neutral text generation for finance-analysis tasks.

The application owns prompts and validates returned JSON. Providers only turn a
prompt into text, making them replaceable without changing routes or domain
rules.
"""
from dataclasses import dataclass
import os

import requests


class AIProviderError(RuntimeError):
    """Raised when the selected provider cannot produce a response."""


@dataclass(frozen=True)
class AIConfiguration:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None


DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "ollama": "llama3.2",
}


def get_ai_configuration() -> AIConfiguration:
    """Load the selected provider, retaining Gemini environment compatibility."""
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    legacy_model = os.getenv("GEMINI_MODEL") if provider == "gemini" else None
    model = os.getenv("AI_MODEL") or legacy_model or DEFAULT_MODELS.get(provider, "")
    provider_key = os.getenv(f"{provider.upper()}_API_KEY")
    api_key = os.getenv("AI_API_KEY") or provider_key
    base_url = os.getenv("AI_BASE_URL")
    return AIConfiguration(provider=provider, model=model, api_key=api_key, base_url=base_url)


def is_ai_configured() -> bool:
    configuration = get_ai_configuration()
    if configuration.provider == "ollama":
        return bool(configuration.model)
    return bool(configuration.api_key and not configuration.api_key.startswith("paste_"))


def generate_text(prompt: str) -> str:
    """Generate text using the configured provider's public SDK or API."""
    configuration = get_ai_configuration()
    if not is_ai_configured():
        raise AIProviderError(f"{configuration.provider} is not configured")

    try:
        if configuration.provider == "gemini":
            from google import genai

            client = genai.Client(api_key=configuration.api_key)
            response = client.models.generate_content(model=configuration.model, contents=prompt)
            return getattr(response, "text", "")

        if configuration.provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=configuration.api_key, base_url=configuration.base_url)
            response = client.chat.completions.create(
                model=configuration.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""

        if configuration.provider == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=configuration.api_key, base_url=configuration.base_url)
            response = client.messages.create(
                model=configuration.model,
                max_tokens=1_000,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in response.content if hasattr(block, "text"))

        if configuration.provider == "ollama":
            base_url = configuration.base_url or "http://127.0.0.1:11434"
            response = requests.post(
                f"{base_url.rstrip('/')}/api/generate",
                json={"model": configuration.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get("response", "")
    except ImportError as error:
        raise AIProviderError(
            f"Install the SDK for provider '{configuration.provider}' before using it"
        ) from error
    except requests.RequestException as error:
        raise AIProviderError(f"{configuration.provider} request failed: {error}") from error
    except Exception as error:
        raise AIProviderError(f"{configuration.provider} generation failed: {error}") from error

    raise AIProviderError(
        f"Unsupported AI_PROVIDER '{configuration.provider}'. "
        "Use gemini, openai, anthropic, or ollama."
    )
