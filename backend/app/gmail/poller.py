import asyncio
import logging

from app.config import settings
from app.gmail.client import GmailClient, HistoryExpiredError

logger = logging.getLogger(__name__)


class GmailPoller:
    """
    Polls Gmail incrementally using the History API.
    Only fetches new messages since the last check — very efficient.
    """

    def __init__(self, client: GmailClient, on_new_email):
        self._client = client
        self._on_new_email = on_new_email  # async callback(EmailMessage)
        self._last_history_id: str | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._last_history_id = self._client.get_current_history_id()
        logger.info(f"Gmail poller started at historyId={self._last_history_id}")

        while self._running:
            await asyncio.sleep(settings.poll_interval_seconds)
            await self._poll()

    def stop(self) -> None:
        self._running = False

    async def _poll(self) -> None:
        try:
            message_ids = self._client.list_new_message_ids(self._last_history_id)
            new_history_id = self._client.get_current_history_id()

            for msg_id in message_ids:
                try:
                    email = self._client.fetch_message(msg_id)
                    logger.info(f"New email: {email}")
                    await self._on_new_email(email)
                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {e}")

            self._last_history_id = new_history_id

        except HistoryExpiredError:
            logger.warning("History ID expired — resetting to current")
            self._last_history_id = self._client.get_current_history_id()

        except Exception as e:
            logger.error(f"Poll error: {e}")
