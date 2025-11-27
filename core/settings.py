from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BotSettings:
    """Runtime configuration for the Bot Framework adapter."""

    app_id: str = os.getenv("MICROSOFT_APP_ID", "")
    app_password: str = os.getenv("MICROSOFT_APP_PASSWORD", "")
    tenant_id: str = os.getenv("MICROSOFT_TENANT_ID", "")

    def has_tenant(self) -> bool:
        return bool(self.tenant_id)
