import os
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from services.ai_client import generate_text, get_ai_configuration, is_ai_configured


class AIClientConfigurationTests(unittest.TestCase):
    def test_uses_legacy_gemini_settings_by_default(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "gemini-key", "GEMINI_MODEL": "gemini-test"},
            clear=True,
        ):
            configuration = get_ai_configuration()

        self.assertEqual(configuration.provider, "gemini")
        self.assertEqual(configuration.model, "gemini-test")
        self.assertEqual(configuration.api_key, "gemini-key")

    def test_selects_openai_with_provider_specific_key(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "openai", "AI_MODEL": "gpt-test", "OPENAI_API_KEY": "openai-key"},
            clear=True,
        ):
            configuration = get_ai_configuration()

        self.assertEqual(configuration.provider, "openai")
        self.assertEqual(configuration.model, "gpt-test")
        self.assertEqual(configuration.api_key, "openai-key")

class AIClientProviderIntegrationTests(unittest.TestCase):
    def test_gemini_returns_mocked_sdk_text(self):
        mock_client = Mock()
        mock_client.models.generate_content.return_value = SimpleNamespace(text='{"status":"ok"}')

        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "gemini", "AI_MODEL": "gemini-test", "AI_API_KEY": "test-key"},
            clear=True,
        ), patch("google.genai.Client", return_value=mock_client) as client_class:
            result = generate_text("test prompt")

        self.assertEqual(result, '{"status":"ok"}')
        client_class.assert_called_once_with(api_key="test-key")
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-test", contents="test prompt"
        )

    def test_openai_returns_mocked_sdk_text(self):
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"status":"ok"}'))]
        )
        mock_openai = Mock(return_value=mock_client)
        openai_module = ModuleType("openai")
        openai_module.OpenAI = mock_openai

        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "openai", "AI_MODEL": "gpt-test", "AI_API_KEY": "test-key"},
            clear=True,
        ), patch.dict(sys.modules, {"openai": openai_module}):
            result = generate_text("test prompt")

        self.assertEqual(result, '{"status":"ok"}')
        mock_openai.assert_called_once_with(api_key="test-key", base_url=None)
        mock_client.chat.completions.create.assert_called_once()

    def test_openai_compatible_providers_use_their_default_base_urls(self):
        providers = {
            "groq": "https://api.groq.com/openai/v1",
            "mistral": "https://api.mistral.ai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "xai": "https://api.x.ai/v1",
            "together": "https://api.together.xyz/v1",
        }

        for provider, base_url in providers.items():
            with self.subTest(provider=provider):
                mock_client = Mock()
                mock_client.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"status":"ok"}'))]
                )
                mock_openai = Mock(return_value=mock_client)
                openai_module = ModuleType("openai")
                openai_module.OpenAI = mock_openai

                with patch.dict(
                    os.environ,
                    {"AI_PROVIDER": provider, "AI_MODEL": "provider-test", "AI_API_KEY": "test-key"},
                    clear=True,
                ), patch.dict(sys.modules, {"openai": openai_module}):
                    result = generate_text("test prompt")

                self.assertEqual(result, '{"status":"ok"}')
                mock_openai.assert_called_once_with(api_key="test-key", base_url=base_url)
                mock_client.chat.completions.create.assert_called_once()

    def test_anthropic_returns_mocked_sdk_text(self):
        mock_client = Mock()
        mock_client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text='{"status":'), SimpleNamespace(text='"ok"}')]
        )
        mock_anthropic = Mock(return_value=mock_client)
        anthropic_module = ModuleType("anthropic")
        anthropic_module.Anthropic = mock_anthropic

        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "anthropic", "AI_MODEL": "claude-test", "AI_API_KEY": "test-key"},
            clear=True,
        ), patch.dict(sys.modules, {"anthropic": anthropic_module}):
            result = generate_text("test prompt")

        self.assertEqual(result, '{"status":"ok"}')
        mock_anthropic.assert_called_once_with(api_key="test-key", base_url=None)
        mock_client.messages.create.assert_called_once()
