import asyncio
import logging
import os

from app.config import settings
from app.gmail.client import GmailClient, HistoryExpiredError

logger = logging.getLogger(__name__)


class GmailPoller:
    """
    Polls Gmail incrementally using the History API.
    Only fetches new messages since the last check — very efficient.

    The last history ID is persisted to disk so that container restarts
    do not cause missed emails during the downtime window.
    """

    def __init__(self, client: GmailClient, on_new_email):
        self._client = client
        self._on_new_email = on_new_email  # async callback(EmailMessage)
        self._last_history_id: str | None = None
        self._running = False

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_history_id(self) -> str | None:
        """Return the saved history ID from disk, or None if not found."""
        try:
            with open(settings.history_id_path, "r") as f:
                value = f.read().strip()
                if value:
                    logger.info(f"Restored history ID from disk: {value}")
                    return value
        except FileNotFoundError:
            pass
        return None

    def _save_history_id(self, history_id: str) -> None:
        """Persist history ID to disk so restarts resume from the same point."""
        try:
            os.makedirs(os.path.dirname(settings.history_id_path), exist_ok=True)
            with open(settings.history_id_path, "w") as f:
                f.write(history_id)
        except Exception as e:
            logger.warning(f"Could not save history ID to disk: {e}")

    # ── Polling loop ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True

        # Try to resume from the last saved position; fall back to current.
        saved = self._load_history_id()
        if saved:
            self._last_history_id = saved
            logger.info(f"Resuming from saved historyId={self._last_history_id}")
        else:
            self._last_history_id = self._client.get_current_history_id()
            self._save_history_id(self._last_history_id)
            logger.info(f"Fresh start — historyId={self._last_history_id}")

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
            self._save_history_id(self._last_history_id)

        except HistoryExpiredError:
            logger.warning("History ID expired — resetting to current")
            self._last_history_id = self._client.get_current_history_id()
            self._save_history_id(self._last_history_id)

        except Exception as e:
            logger.error(f"Poll error: {e}")
