"""Simple smoke test to validate language control behavior with alternating languages.

This script sends sample user messages and orchestrate responses through the
Watsonx.ai language control layer to confirm that the final reply matches the
user's language (English or Spanish only).

Usage:
    python scripts/run_language_roundtrip.py

Environment:
    Requires the Watsonx.ai settings (WX_APIKEY, WX_PROJECT_ID, WX_URL, etc.)
    to be present. The script exits early if the integration is not enabled.
"""

from typing import List, Tuple
import os

from conversation.watsonx_ai import WatsonxAI
from conversation.watsonx_ai_settings import WatsonxAISettings

Scenario = Tuple[str, str, str]


def _build_scenarios() -> List[Scenario]:
    """Return alternating Spanish/English test cases."""
    return [
        (
            "es-ES",
            "Hola, ¿puedes ayudarme a resumir este documento?",
            "Sure, I can summarize that document for you.",
        ),
        (
            "en-US",
            "Can you draft an email for the client?",
            "Claro, puedo redactar ese correo para el cliente.",
        ),
        (
            "es-ES",
            "Dame tres ideas para mejorar la satisfacción del cliente",
            "Here are three ideas to improve customer satisfaction:",
        ),
        (
            "en-US",
            "List two next steps for the sales follow-up",
            "Aquí tienes dos próximos pasos para el seguimiento de ventas:",
        ),
    ]


def main() -> None:
    settings = WatsonxAISettings()
    if not settings.is_enabled():
        print("Watsonx.ai is not enabled. Please set WX_APIKEY and WX_PROJECT_ID.")
        return

    api_key = os.getenv("WX_APIKEY", settings.api_key)
    client = WatsonxAI(settings, api_key)

    for index, (locale, user_message, orchestrate_response) in enumerate(_build_scenarios(), start=1):
        print(f"\n--- Scenario {index} ({locale}) ---")
        print(f"User message: {user_message}")
        print(f"Orchestrate response: {orchestrate_response}")

        final_response = client.control_language_response(
            user_message=user_message,
            orchestrate_response=orchestrate_response,
            user_locale=locale,
        )

        print("Final response:")
        print(final_response or "<no response returned>")


if __name__ == "__main__":
    main()
