from dataclasses import dataclass, replace
from typing import Dict, Any, Optional
from botbuilder.schema import Activity


@dataclass(frozen=True)
class TeamsActivityContext:
    conversation_id: str
    user_name: str
    user_id: str
    user_aad_object_id: str
    user_email: str
    user_phone: str
    locale: str
    message: str


class TeamsContextBuilder:
    """Transforms Bot Framework Activities into Watson-ready context payloads."""

    def from_activity(self, activity: Activity) -> TeamsActivityContext:
        from_account = activity.from_property
        return TeamsActivityContext(
            conversation_id=activity.conversation.id,
            user_name=from_account.name,
            user_id=from_account.id,
            user_aad_object_id=getattr(from_account, "aad_object_id", ""),
            user_email=self._extract_contact_value(
                from_account,
                keys=[
                    "email",
                    "mail",
                    "userPrincipalName",
                    "primaryEmail",
                ],
            ),
            user_phone=self._extract_contact_value(
                from_account,
                keys=[
                    "mobilePhone",
                    "mobile_phone",
                    "phone",
                    "telephoneNumber",
                ],
            ),
            locale=activity.locale or "es-ES",
            message=activity.text or "",
        )

    def merge_profile_data(
        self,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]],
    ) -> TeamsActivityContext:
        if not profile:
            return context

        email = context.user_email or self._extract_from_mapping(
            profile,
            keys=[
                "mail",
                "email",
                "userPrincipalName",
                "primaryEmail",
            ],
        )
        phone = context.user_phone or self._extract_from_mapping(
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
        aad_object_id = context.user_aad_object_id or str(
            profile.get("id")
            or profile.get("aad_object_id")
            or profile.get("objectId")
            or ""
        )

        return replace(
            context,
            user_email=email,
            user_phone=phone,
            user_aad_object_id=aad_object_id,
        )

    def to_watson_context(
        self,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "channel": {
                "channel_type": "teams",
                "teams": {
                    "conversation_id": context.conversation_id,
                    "user_name": context.user_name,
                    "user_aadObjectId": context.user_aad_object_id,
                    "user_id": context.user_id,
                },
                "locale": context.locale,
            }
        }
        if profile:
            for key, value in profile.items():
                payload["channel"]["teams"][f"profile_{key}"] = value
        
        return payload

    @staticmethod
    def _extract_contact_value(account: Any, keys) -> str:
        if not account:
            return ""

        def _coerce(value: Any) -> str:
            if isinstance(value, list):
                return next((str(item) for item in value if item), "")
            if value is None:
                return ""
            return str(value)

        for key in keys:
            value = getattr(account, key, None)
            if value:
                coerced = _coerce(value)
                if coerced:
                    return coerced

        additional_props = getattr(account, "additional_properties", None) or getattr(
            account, "properties", None
        )
        if isinstance(additional_props, dict):
            for key in keys:
                value = additional_props.get(key)
                if value:
                    coerced = _coerce(value)
                    if coerced:
                        return coerced

        return ""

    @staticmethod
    def _extract_from_mapping(data: Dict[str, Any], keys) -> str:
        for key in keys:
            if key not in data:
                continue
            value = data[key]
            if isinstance(value, list):
                return next((str(item) for item in value if item), "")
            if isinstance(value, dict):
                return next((str(v) for v in value.values() if v), "")
            if value:
                return str(value)
        return ""
