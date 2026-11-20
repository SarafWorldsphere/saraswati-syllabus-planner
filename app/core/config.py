"""Process settings. One database serves every school; the host picks which one."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://swais:swais_secret@localhost:5434/syllabus_planner"
    SARASWATI_DATABASE_URL: str = ""
    SECRET_KEY: str = "dev-syllabus-planner-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8010

    CORS_ORIGINS: str = "http://localhost:3000"

    # Bound to every host while APP_ENV is development. Production resolves
    # the host through platform.tenant_domains and ignores this value.
    DEV_TENANT_ID: str = "11111111-1111-4111-8111-111111111111"

    AI_SERVICE_URL: str = ""
    PERIOD_MINUTES: int = 45

    DB_SERVICE_SLOTS: int = 12
    DB_RESERVE: float = 0.2

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
