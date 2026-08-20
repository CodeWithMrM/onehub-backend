"""
Centralized application configuration, loaded from environment
variables. Import `settings` everywhere instead of calling
os.getenv() directly, so every config value is validated in one
place.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = ""
    DIRECT_DATABASE_URL: str = ""

    CLERK_SECRET_KEY: str = ""
    CLERK_JWT_ISSUER: str = ""

    REDIS_URL: str = ""

    CORS_ORIGINS: str = ""

    DEV_ADMIN_CLERK_USER_ID: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
