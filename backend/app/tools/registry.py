import logging

from app.models import EmailMessage
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all automation tools.
    Each email is checked against all registered tools.
    Multiple tools can trigger on the same email.
    """

    def __init__(self):
        self._tools: list[BaseTool] = []

    def register(self, tool: BaseTool) -> None:
        self._tools.append(tool)
        logger.info(f"Tool registered: {tool.name}")

    async def dispatch(self, email: EmailMessage) -> None:
        triggered = 0
        for tool in self._tools:
            try:
                if await tool.should_trigger(email):
                    logger.info(f"Tool '{tool.name}' triggered for email {email.id}")
                    await tool.execute(email)
                    triggered += 1
            except Exception as e:
                logger.error(f"Tool '{tool.name}' failed on email {email.id}: {e}")

        if triggered == 0:
            logger.debug(f"No tools triggered for email {email.id} (subject: {email.subject!r})")
