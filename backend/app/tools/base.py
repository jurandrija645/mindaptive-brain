from abc import ABC, abstractmethod

from app.models import EmailMessage


class BaseTool(ABC):
    """
    Base class for all email automation tools.

    To add a new automation:
    1. Create a new file in app/tools/
    2. Subclass BaseTool
    3. Implement should_trigger() and execute()
    4. Register it in app/tools/registry.py
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name for logging."""

    @abstractmethod
    async def should_trigger(self, email: EmailMessage) -> bool:
        """Return True if this tool should handle the given email."""

    @abstractmethod
    async def execute(self, email: EmailMessage) -> None:
        """Perform the automation action for this email."""
