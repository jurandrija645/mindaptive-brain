import base64
import logging
import re
from email import message_from_bytes
from email.header import decode_header

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings
from app.models import EmailMessage

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _decode_mime_words(s: str) -> str:
    """Decode RFC 2047 encoded words in email headers."""
    parts = decode_header(s)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg) -> tuple[str, str]:
    """Extract plain text and HTML body from email.message.Message."""
    text, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not text:
                text = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif ct == "text/html" and not html:
                html = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            ct = msg.get_content_type()
            content = payload.decode("utf-8", errors="replace")
            if ct == "text/html":
                html = content
            else:
                text = content
    return text, html


class GmailClient:
    def __init__(self):
        self._service = None

    def authenticate(self) -> None:
        creds = None

        try:
            creds = Credentials.from_authorized_user_file(settings.gmail_token_path, SCOPES)
        except FileNotFoundError:
            logger.info("No token.json found — starting OAuth flow")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Gmail token refreshed")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail OAuth flow completed")

            with open(settings.gmail_token_path, "w") as f:
                f.write(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail client authenticated")

    def get_current_history_id(self) -> str:
        profile = self._service.users().getProfile(userId="me").execute()
        return profile["historyId"]

    def list_new_message_ids(self, start_history_id: str) -> list[str]:
        """Return message IDs added since start_history_id."""
        message_ids = []
        try:
            response = self._service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
            ).execute()

            for record in response.get("history", []):
                for added in record.get("messagesAdded", []):
                    msg = added["message"]
                    # Skip drafts and sent mail
                    if "DRAFT" not in msg.get("labelIds", []) and "SENT" not in msg.get("labelIds", []):
                        message_ids.append(msg["id"])

        except Exception as e:
            # historyId too old — caller should reset
            if "404" in str(e) or "invalidHistoryId" in str(e):
                raise HistoryExpiredError() from e
            raise

        return message_ids

    def fetch_message(self, message_id: str) -> EmailMessage:
        raw = self._service.users().messages().get(
            userId="me", id=message_id, format="raw"
        ).execute()

        raw_bytes = base64.urlsafe_b64decode(raw["raw"] + "==")
        msg = message_from_bytes(raw_bytes)

        subject = _decode_mime_words(msg.get("Subject", ""))
        from_header = msg.get("From", "")
        to_header = msg.get("To", "")
        date_header = msg.get("Date", "")

        # Parse "Name <email>" or just "email"
        match = re.match(r'^"?([^"<]*)"?\s*<?([^>]*)>?$', from_header.strip())
        if match:
            from_name = match.group(1).strip()
            from_email = match.group(2).strip()
        else:
            from_name = ""
            from_email = from_header

        body_text, body_html = _extract_body(msg)

        return EmailMessage(
            id=raw["id"],
            thread_id=raw["threadId"],
            subject=subject,
            from_email=from_email,
            from_name=from_name,
            to=to_header,
            date=date_header,
            body_text=body_text,
            body_html=body_html,
            labels=raw.get("labelIds", []),
            raw=raw,
        )


class HistoryExpiredError(Exception):
    """Raised when the history ID is too old and needs a reset."""
