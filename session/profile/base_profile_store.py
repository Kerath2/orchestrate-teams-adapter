from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ProfileStore(ABC):
    """Defines caching operations for user profile data."""

    @abstractmethod
    def save_profile(self, object_id: str, profile: Dict[str, Any]) -> None:
        """Persist the profile payload."""
        raise NotImplementedError

    @abstractmethod
    def get_profile(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached profile payload, if available."""
        raise NotImplementedError

    @abstractmethod
    def delete_profile(self, object_id: str) -> None:
        """Remove a cached profile."""
        raise NotImplementedError
