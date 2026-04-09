import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self._client = WebClient(token=settings.slack_bot_token)

    def send_message(self, channel: str, text: str, blocks: list | None = None) -> None:
        try:
            kwargs = {"channel": channel, "text": text}
            if blocks:
                kwargs["blocks"] = blocks
            self._client.chat_postMessage(**kwargs)
            logger.info(f"Slack message sent to #{channel}")
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            raise
