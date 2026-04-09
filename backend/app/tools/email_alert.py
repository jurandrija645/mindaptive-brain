from app.config import settings
from app.models import EmailMessage
from app.slack.client import SlackClient
from app.tools.base import BaseTool


class EmailAlertTool(BaseTool):
    """
    Sends a Slack notification when an email arrives from a watched address.
    """

    name = "email_alert"

    def __init__(self, slack: SlackClient, watch_address: str):
        self._slack = slack
        self._watch_address = watch_address.lower()

    async def should_trigger(self, email: EmailMessage) -> bool:
        return self._watch_address in email.from_email.lower()

    async def execute(self, email: EmailMessage) -> None:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📬 New Email Received", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*From:*\n{email.from_name or email.from_email}"},
                    {"type": "mrkdwn", "text": f"*Email:*\n{email.from_email}"},
                    {"type": "mrkdwn", "text": f"*Subject:*\n{email.subject}"},
                ],
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": email.date}],
            },
        ]

        self._slack.send_message(
            channel=settings.slack_meeting_channel,
            text=f"New email from {email.from_email}: {email.subject}",
            blocks=blocks,
        )
