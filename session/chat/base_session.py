from abc import ABC, abstractmethod
from typing import Optional

class ChatBaseSessionManager(ABC):
    """Abstract base class for session management."""

    @abstractmethod
    def save_thread(self, conversation_id: str, thread_id: str) -> None:
        """Save a thread_id associated with a given conversation_id."""
        pass

    @abstractmethod
    def get_thread(self, conversation_id: str) -> Optional[str]:
        """Retrieve a thread_id associated with a given conversation_id."""
        pass

    @abstractmethod
    def delete_thread(self, conversation_id: str) -> None:
        """Delete a user's session."""
        pass
