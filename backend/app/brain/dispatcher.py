import logging

from app.models import EmailMessage
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class Dispatcher:
    """
    The brain of the system.
    Receives every incoming email and routes it to registered tools.
    Future: will also handle LLM-driven decisions.
    """

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    async def process(self, email: EmailMessage) -> None:
        logger.debug(f"Dispatcher processing: {email}")
        await self._registry.dispatch(email)
