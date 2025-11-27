import json
import logging
from typing import Optional, Dict, Any

import redis

from session.redis_settings import RedisSessionSettings
from .base_profile_store import ProfileStore

logger = logging.getLogger(__name__)


class RedisProfileStore(ProfileStore):
    """Caches user profiles in Redis with a configurable TTL."""

    def __init__(
        self,
        settings: Optional[RedisSessionSettings] = None,
        expire_seconds: int = 86400,
    ):
        self.settings = settings or RedisSessionSettings()
        self.expire_seconds = expire_seconds
        connection_kwargs = self.settings.as_dict()
        self.redis_client = redis.Redis(**connection_kwargs)
        logger.info(
            "RedisProfileStore initialized host=%s db=%s expire_seconds=%s",
            connection_kwargs.get("host"),
            connection_kwargs.get("db"),
            expire_seconds,
        )

    def save_profile(self, object_id: str, profile: Dict[str, Any]) -> None:
        key = self._key(object_id)
        logger.debug("Caching profile for object_id=%s", object_id)
        self.redis_client.setex(key, self.expire_seconds, json.dumps(profile))

    def get_profile(self, object_id: str) -> Optional[Dict[str, Any]]:
        key = self._key(object_id)
        cached = self.redis_client.get(key)
        if not cached:
            logger.debug("Profile cache miss for object_id=%s", object_id)
            return None
        logger.debug("Profile cache hit for object_id=%s", object_id)
        return json.loads(cached)

    def delete_profile(self, object_id: str) -> None:
        key = self._key(object_id)
        self.redis_client.delete(key)

    def _key(self, object_id: str) -> str:
        return f"profile:{object_id}"
