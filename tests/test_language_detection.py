import unittest

from conversation.watsonx_ai import WatsonxAI
from conversation.watsonx_ai_settings import WatsonxAISettings


class WatsonxLanguageDetectionTests(unittest.TestCase):
    def setUp(self):
        settings = WatsonxAISettings(api_key="dummy", project_id="dummy")
        self.client = WatsonxAI(settings=settings, api_key="dummy")

    def test_detects_english_over_spanish_locale(self):
        language = self.client._determine_target_language(  # noqa: SLF001
            "Please summarize the quarterly numbers in one paragraph.",
            "es-ES",
        )
        self.assertEqual(language, "English")

    def test_detects_spanish_over_english_locale(self):
        language = self.client._determine_target_language(  # noqa: SLF001
            "Necesito el estado del proyecto y los próximos pasos.",
            "en-US",
        )
        self.assertEqual(language, "Spanish")

    def test_falls_back_to_locale_when_detection_missing(self):
        language = self.client._determine_target_language(  # noqa: SLF001
            "ok",  # too short to detect reliably
            "fr-FR",
        )
        self.assertEqual(language, "French")

    def test_retries_translation_when_primary_not_in_target(self):
        class StubWatsonxAI(WatsonxAI):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.calls = 0

            def _generate_text(self, prompt: str):
                self.calls += 1
                if self.calls == 1:
                    return "Hola, puedo ayudarte"  # Wrong language
                if self.calls == 2:
                    return "fr: Bonjour, je peux aider"  # Still wrong language
                return "en: Hello, final pass"

        stub = StubWatsonxAI(
            settings=WatsonxAISettings(api_key="dummy", project_id="dummy"),
            api_key="dummy",
        )
        final = stub.control_language_response(
            user_message="hello",
            orchestrate_response="¡Hola! ¿En qué puedo ayudarte hoy?",
            user_locale="en-US",
        )
        self.assertEqual(final, "Hello, final pass")

    def test_strips_prompt_artifacts(self):
        class ArtifactStub(WatsonxAI):
            def _generate_text(self, prompt: str):
                return "Hola!\nTEXT:\nextra\n[Answer] more"

        stub = ArtifactStub(
            settings=WatsonxAISettings(api_key="dummy", project_id="dummy"),
            api_key="dummy",
        )
        final = stub.control_language_response(
            user_message="hola",
            orchestrate_response="Hello!",
            user_locale="es-ES",
        )
        self.assertEqual(final, "Hola!")


if __name__ == "__main__":
    unittest.main()
