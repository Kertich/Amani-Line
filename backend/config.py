from functools import lru_cache

from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    cors_origins: str = "http://localhost:5173"
    storage_bucket: str = "report-attachments"
    
    
    # Add the database_url field so Pydantic expects it from your .env
    database_url: str = Field(default="postgresql+asyncpg://fallback_if_missing")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
         extra="ignore"  # 💡 Pro-Tip: Changing "forbid" to "ignore" prevents future unexpected .env fields from crashing your app
        )
    
    

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
