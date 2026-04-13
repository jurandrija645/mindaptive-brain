import logging
import re

from app.config import settings
from app.models import EmailMessage
from app.slack.client import SlackClient
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

CALENDLY_DOMAIN = "calendly.com"
MEETING_PATTERN = re.compile(r"(.+?)(?:'s|'\s*s)?\s+(\d+\s+Minute\s+Meeting)", re.IGNORECASE)
DATETIME_PATTERN = re.compile(
    r"(?:on\s+)?(\w+day,\s+\w+\s+\d+,\s+\d{4}\s+at\s+[\d:apm\s]+(?:\(.*?\))?)", re.IGNORECASE
)


class CalendlyMeetingTool(BaseTool):
    """
    Detects Calendly meeting booked/reminder notifications
    and sends a Slack alert to the configured channel.
    """

    name = "calendly_meeting"

    def __init__(self, slack: SlackClient):
        self._slack = slack

    async def should_trigger(self, email: EmailMessage) -> bool:
        return CALENDLY_DOMAIN in email.from_email.lower()

    async def execute(self, email: EmailMessage) -> None:
        # Extract person name from subject: "Reminder: Peter Dublin's 30 Minute Meeting..."
        # or "Peter Dublin's 30 Minute Meeting is coming up."
        subject = email.subject
        person_name = ""
        meeting_type = ""

        # Try to extract from "Reminder: Name's X Minute Meeting"
        clean_subject = re.sub(r"^Reminder:\s*", "", subject, flags=re.IGNORECASE).strip()
        match = re.match(r"(.+?)(?:'s|'s)\s+(.+?meeting)", clean_subject, re.IGNORECASE)
        if match:
            person_name = match.group(1).strip()
            meeting_type = match.group(2).strip()

        # Extract datetime from body
        body = email.body_text or email.body_html
        dt_match = DATETIME_PATTERN.search(body)
        meeting_time = dt_match.group(1).strip() if dt_match else "See email for details"

        is_reminder = "reminder" in subject.lower()
        header = "⏰ Meeting Reminder" if is_reminder else "📅 New Meeting Booked!"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header, "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Person:*\n{person_name or 'See email'}"},
                    {"type": "mrkdwn", "text": f"*Meeting:*\n{meeting_type or subject}"},
                    {"type": "mrkdwn", "text": f"*When:*\n{meeting_time}"},
                    {"type": "mrkdwn", "text": f"*Via:*\nCalendly"},
                ],
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": email.date}],
            },
        ]

        self._slack.send_message(
            channel=settings.slack_meeting_channel,
            text=f"{header}: {person_name} — {meeting_type}",
            blocks=blocks,
        )
        logger.info(f"Calendly notification sent for {person_name}")
