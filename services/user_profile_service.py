import logging
from typing import Optional, Dict, Any

import requests

from services.user_profile_settings import UserProfileSettings
from session.profile import ProfileStore

logger = logging.getLogger(__name__)


class UserProfileService:
    """Fetches and caches Teams user profile information."""

    def __init__(
        self,
        settings: UserProfileSettings,
        store: ProfileStore,
    ):
        self._settings = settings
        self._store = store

    def get_user_profile(self, object_id: str) -> Optional[Dict[str, Any]]:
        if not object_id:
            logger.debug("User profile lookup skipped: missing object_id.")
            return None
        cached = self._store.get_profile(object_id)
        if cached:
            return cached

        if not self._settings.is_enabled():
            logger.warning("User profile lookup disabled by configuration.")
            return None

        profile = self._fetch_profile(object_id)
        if profile:
            self._store.save_profile(object_id, profile)
        return profile

    def _fetch_profile(self, object_id: str) -> Optional[Dict[str, Any]]:
        params = {"object_id": object_id}
        headers = {
            "Accept": "application/json",
            "Client-Secret": self._settings.client_secret,
        }
        try:
            logger.info("Requesting profile for object_id=%s", object_id)
            response = requests.get(
                self._settings.base_url,
                headers=headers,
                params=params,
                timeout=self._settings.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("user")
        except requests.RequestException as exc:
            logger.exception("Failed to fetch profile for object_id=%s", object_id)
            return None
