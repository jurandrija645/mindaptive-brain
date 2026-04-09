import logging
import re

from app.config import settings
from app.models import EmailMessage
from app.slack.client import SlackClient
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

HUBSPOT_SENDER = "noreply@notifications.hubspot.com"
SUBJECT_PATTERN = re.compile(r"prospect booked meeting", re.IGNORECASE)
PROSPECT_PATTERN = re.compile(r"([A-Za-z]+)\s+([\w.+-]+@[\w.-]+)", re.IGNORECASE)


def _extract_prospect(body: str) -> tuple[str, str]:
    """Try to extract prospect name and email from the email body."""
    match = PROSPECT_PATTERN.search(body)
    if match:
        return match.group(1), match.group(2)
    return "Unknown", ""


class HubspotMeetingTool(BaseTool):
    """
    Detects HubSpot 'Prospect booked meeting' notifications
    and sends a Slack alert to the configured channel.
    """

    name = "hubspot_meeting_booked"

    def __init__(self, slack: SlackClient):
        self._slack = slack

    async def should_trigger(self, email: EmailMessage) -> bool:
        return (
            HUBSPOT_SENDER in email.from_email.lower()
            and bool(SUBJECT_PATTERN.search(email.subject))
        )

    async def execute(self, email: EmailMessage) -> None:
        # Extract company name from subject: "Prospect booked meeting - CompanyName"
        company = ""
        subject_parts = email.subject.split(" - ", 1)
        if len(subject_parts) == 2:
            company = subject_parts[1].strip()

        # Extract prospect info from body
        body = email.body_text or email.body_html
        prospect_name, prospect_email = _extract_prospect(body)

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📅 New Meeting Booked!", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Prospect:*\n{prospect_name}"},
                    {"type": "mrkdwn", "text": f"*Email:*\n{prospect_email or 'N/A'}"},
                    {"type": "mrkdwn", "text": f"*Company:*\n{company or 'N/A'}"},
                    {"type": "mrkdwn", "text": f"*Subject:*\n{email.subject}"},
                ],
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Via HubSpot | {email.date}"}],
            },
        ]

        fallback_text = f"New meeting booked: {prospect_name} ({prospect_email}) from {company}"
        self._slack.send_message(
            channel=settings.slack_meeting_channel,
            text=fallback_text,
            blocks=blocks,
        )
        logger.info(f"Meeting booked notification sent for {prospect_name} / {company}")
