import time
import logging
from typing import Optional
from .base_session import ChatBaseSessionManager

logger = logging.getLogger(__name__)

class ChatMemorySessionManager(ChatBaseSessionManager):
    """In-memory session manager."""
    
    def __init__(self, expire_seconds=900):
        self.store = {}
        self.expire_seconds = expire_seconds

    def save_thread(self, conversation_id: str, thread_id: str) -> None:
        expire_at = time.time() + self.expire_seconds
        logger.debug(f"Saving thread_id for conversation_id {conversation_id} with expiration {self.expire_seconds} seconds.")
        self.store[conversation_id] = {"thread_id": thread_id, "expire_at": expire_at}

    def get_thread(self, conversation_id: str) -> Optional[str]:
        data = self.store.get(conversation_id)
        logger.debug(f"Retrieving thread_id for conversation_id {conversation_id}.")
        if data and time.time() < data["expire_at"]:
            return data["thread_id"]
        if data:
            del self.store[conversation_id]
        return None

    def delete_thread(self, conversation_id: str) -> None:
        logger.debug(f"Deleting thread_id for conversation_id {conversation_id}.")
        self.store.pop(conversation_id, None)
