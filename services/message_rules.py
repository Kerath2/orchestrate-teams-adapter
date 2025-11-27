from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from services.context_builder import TeamsActivityContext


class MessageRule(ABC):
    """Defines the contract for rules that can transform outgoing user messages."""

    @abstractmethod
    def apply(
        self,
        message: str,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return the transformed message."""
        raise NotImplementedError


class LocaleResponseRule(MessageRule):
    """
    Appends language instructions based on the Teams locale.

    - Locales starting with `es-` force Spanish responses.
    - Any other locale defaults to English responses.
    """

    def __init__(
        self,
        spanish_instruction: str = "ALWAYS respond in Spanish. NEVER use Markdown table formats to reply.",
        english_instruction: str = "ALWAYS respond in English. NEVER use Markdown table formats to reply.",
    ):
        self._spanish_instruction = spanish_instruction
        self._english_instruction = english_instruction

    def apply(
        self,
        message: str,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        locale = (context.locale or "").lower()
        instruction = (
            self._spanish_instruction if locale.startswith("es-") else self._english_instruction
        )

        if instruction in message:
            return message

        separator = "\n\n" if message else ""
        return f"{message}{separator}{instruction}"


class UserInputLabelRule(MessageRule):
    """
    Wraps the raw Teams message so downstream instructions are clearly separated.
    """

    def __init__(self, label: str = "USER_INPUT"):
        self._label = label

    def apply(
        self,
        message: str,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not message:
            return message

        prefix = f"{self._label}: "
        if message.startswith(prefix):
            return message

        return f"{prefix}'{message}'"


class ArgumentsPrefixRule(MessageRule):
    """
    Adds an ARGUMENTS block at the beginning of the prompt with user identifiers.
    """

    def apply(
        self,
        message: str,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        prefix = self._build_prefix(context, profile)

        if message.startswith(prefix):
            return message

        separator = "\n\n" if message else ""
        return f"{prefix}{separator}{message}"

    def _build_prefix(
        self,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]],
    ) -> str:
        profile = profile or {}
        email = context.user_email or self._extract_first(
            profile,
            keys=[
                "mail",
                "email",
                "userPrincipalName",
                "primaryEmail",
            ],
        )
        phone = context.user_phone or self._extract_first(
            profile,
            keys=[
                "mobilePhone",
                "mobile_phone",
                "mobile",
                "businessPhones",
                "phone",
                "telephoneNumber",
            ],
        )
        aad_object_id = context.user_aad_object_id

        parts = []
        if email:
            parts.append(f"email:'{email}'")
        if aad_object_id:
            parts.append(f"aad_object_id:'{aad_object_id}'")
        if phone:
            parts.append(f"phone:'{phone}'")

        arguments = "\n".join(parts)
        return f"{arguments}".rstrip()

    @staticmethod
    def _extract_first(profile: Dict[str, Any], keys) -> Optional[str]:
        for key in keys:
            if key not in profile:
                continue
            value = profile[key]
            if isinstance(value, list):
                return next((item for item in value if item), None)
            if isinstance(value, dict):
                # grab first non-empty value in dict
                return next((str(v) for v in value.values() if v), None)
            if value:
                return str(value)
        return None
