import os
import unittest
from unittest.mock import patch

from services.ai_client import get_ai_configuration, is_ai_configured


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

    def test_ollama_does_not_require_an_api_key(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "ollama", "AI_MODEL": "llama3.2"}, clear=True):
            self.assertTrue(is_ai_configured())
