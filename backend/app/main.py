import asyncio
import logging
import logging.config

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.gmail.client import GmailClient
from app.gmail.poller import GmailPoller
from app.slack.client import SlackClient
from app.tools.registry import ToolRegistry
from app.tools.hubspot_meeting import HubspotMeetingTool
from app.tools.email_alert import EmailAlertTool
from app.brain.dispatcher import Dispatcher

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── App wiring ────────────────────────────────────────────────────────────────

def build_registry(slack: SlackClient) -> ToolRegistry:
    """
    Register all automation tools here.
    To add a new tool: instantiate it and call registry.register(tool).
    """
    registry = ToolRegistry()
    registry.register(HubspotMeetingTool(slack=slack))
    registry.register(EmailAlertTool(slack=slack, watch_address="mindaptive@gmail.com"))
    # registry.register(YourNextTool(...))
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mindaptive Brain...")

    gmail = GmailClient()
    gmail.authenticate()

    slack = SlackClient()
    registry = build_registry(slack)
    dispatcher = Dispatcher(registry)

    poller = GmailPoller(
        client=gmail,
        on_new_email=dispatcher.process,
    )

    task = asyncio.create_task(poller.start())
    logger.info("Gmail poller running")

    yield  # app is live

    logger.info("Shutting down...")
    poller.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Mindaptive Brain",
    description="Email automation and intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
