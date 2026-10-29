from functools import lru_cache

from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    cors_origins: str = "http://localhost:5173"
    storage_bucket: str = "report-attachments"
    admin_emails: str = ""
    verification_queue_emails: str = ""
    database_url: str = Field(default="postgresql+asyncpg://fallback_if_missing")
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_chat_model: str = "gpt-4o-mini"
    ai_transcription_model: str = "whisper-1"
    at_callback_secret: str = ""
    at_allowed_ips: str = ""
    at_api_key: str = ""
    at_username: str = "sandbox"
    at_sms_url: str = "https://api.sandbox.africastalking.com/version1/messaging"
    at_shortcode: str = "40404"
    reporter_hmac_pepper: str = ""
    reporter_phone_encryption_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def verification_queue_email_set(self) -> set[str]:
        return {
            email.strip().casefold()
            for email in self.verification_queue_emails.split(",")
            if email.strip()
        }

    @property
    def admin_email_set(self) -> set[str]:
        return {
            email.strip().casefold()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @property
    def at_allowed_ip_set(self) -> set[str]:
        return {ip.strip() for ip in self.at_allowed_ips.split(",") if ip.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
