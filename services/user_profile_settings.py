from dataclasses import dataclass
import os


@dataclass(frozen=True)
class UserProfileSettings:
    """Settings for the external user profile lookup."""

    base_url: str = os.getenv("USER_PROFILE_API_URL")
    client_secret: str = os.getenv("USER_PROFILE_CLIENT_SECRET", "")
    timeout_seconds: int = int(os.getenv("USER_PROFILE_TIMEOUT_SECONDS", "10"))

    def is_enabled(self) -> bool:
        return bool(self.base_url and self.client_secret)
