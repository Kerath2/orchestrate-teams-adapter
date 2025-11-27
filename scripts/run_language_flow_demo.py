"""
Demo script to exercise the language controller with mixed-language inputs
using the real Watsonx.ai language control (no mocks).
"""

from typing import List, Dict
import pathlib
import sys

from dotenv import load_dotenv

# Ensure repo root is on sys.path when running directly
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conversation.watsonx_ai import WatsonxAI  # noqa: E402
from conversation.watsonx_ai_settings import WatsonxAISettings  # noqa: E402


def ensure_config():
    load_dotenv(dotenv_path=ROOT / ".env", override=True)
    settings = WatsonxAISettings()
    if not settings.is_enabled():
        raise SystemExit(
            "Watsonx.ai no está configurado: define WX_APIKEY y WX_PROJECT_ID en tu entorno/.env"
        )
    return settings


def run_demo():
    settings = ensure_config()
    language_controller = WatsonxAI(settings=settings, api_key=settings.api_key)

    scenarios: List[Dict[str, str]] = [
        {
            "user_message": "hola",
            "locale": "es-ES",
            "orchestrate_response": "Hello! How can I help you today?",
        },
        {
            "user_message": "hello",
            "locale": "en-US",
            "orchestrate_response": "¡Hola! ¿En qué puedo ayudarte hoy?",
        },
        {
            "user_message": "ver opciones",
            "locale": "es-ES",
            "orchestrate_response": "Here are your options: check channels, create ticket, or get help.",
        },
        {
            "user_message": "see options",
            "locale": "en-US",
            "orchestrate_response": "Estas son tus opciones: ver canales, crear ticket o pedir ayuda.",
        },
        {
            "user_message": "ver canales",
            "locale": "es-ES",
            "orchestrate_response": "I can list your channels or create a new ticket.",
        },
        {
            "user_message": "see channels",
            "locale": "en-US",
            "orchestrate_response": "Puedo listar tus canales o crear un ticket nuevo.",
        },
        {
            "user_message": "crear ticket",
            "locale": "es-ES",
            "orchestrate_response": "I can create a ticket for you. Please provide the details.",
        },
        {
            "user_message": "create ticket",
            "locale": "en-US",
            "orchestrate_response": "Puedo crear un ticket para ti. Proporciona los detalles.",
        },
    ]

    print("=== Language Control Demo (real Watsonx.ai translation) ===\n")
    for scenario in scenarios:
        final = language_controller.control_language_response(
            user_message=scenario["user_message"],
            orchestrate_response=scenario["orchestrate_response"],
            user_locale=scenario["locale"],
        )
        print(f"User message: {scenario['user_message']} (locale: {scenario['locale']})")
        print(f"Orchestrate response: {scenario['orchestrate_response']}")
        print(f"Final response: {final}")
        print("-" * 60)


if __name__ == "__main__":
    run_demo()
