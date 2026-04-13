from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gmail
    gmail_token_path: str = "credentials/token.json"
    gmail_credentials_path: str = "credentials/client_secret.json"
    gmail_user: str = "me"

    # Slack
    slack_bot_token: str
    slack_meeting_channel: str = "danteov-kanal"

    # Polling
    poll_interval_seconds: int = 30
    history_id_path: str = "credentials/last_history_id.txt"

    # App
    environment: str = "production"
    log_level: str = "INFO"


settings = Settings()
