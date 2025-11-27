import redis
import json
from typing import Optional
import logging
from session.redis_settings import RedisSessionSettings
from .base_session import ChatBaseSessionManager

logger = logging.getLogger(__name__)

class ChatRedisSessionManager(ChatBaseSessionManager):
    def __init__(
        self,
        settings: Optional[RedisSessionSettings] = None,
        expire_seconds: int = 900
    ):
        """
        Initialize the SessionManager with a Redis connection.

        :param settings: RedisSessionSettings object containing connection parameters.
        :param expire_seconds: Expiration time in seconds (default: 900 = 15 minutes).
        """
        self.settings = settings or RedisSessionSettings()
        connection_kwargs = self.settings.as_dict()
        self.redis_client = redis.Redis(**connection_kwargs)
        self.expire_seconds = expire_seconds
        logger.info(
            "ChatRedisSessionManager initialized host=%s db=%s expire_seconds=%s",
            connection_kwargs.get("host"),
            connection_kwargs.get("db"),
            expire_seconds
        )

    def save_thread(self, conversation_id: str, thread_id: str) -> None:
        """Save a thread_id associated with a given conversation_id, with expiration time."""
        key = f"session:{conversation_id}"
        data = {"thread_id": thread_id}
        logger.debug(f"Saving thread_id for conversation_id {conversation_id} with expiration {self.expire_seconds} seconds.")
        self.redis_client.setex(key, self.expire_seconds, json.dumps(data))

    def get_thread(self, conversation_id: str) -> Optional[str]:
        """Retrieve the thread_id associated with a given conversation_id, if it has not expired."""
        key = f"session:{conversation_id}"
        data = self.redis_client.get(key)
        logger.debug(f"Retrieving thread_id for conversation_id {conversation_id}.")
        if data:
            return json.loads(data).get("thread_id")
        return None

    def delete_thread(self, conversation_id: str) -> None:
        """Manually delete a user's session from Redis."""
        key = f"session:{conversation_id}"
        logger.debug(f"Deleting thread_id for conversation_id {conversation_id}.")
        self.redis_client.delete(key)
