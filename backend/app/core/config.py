from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Catalyst ElderCare Platform"
    ENVIRONMENT: str = "development"

    # Security & Token Configs
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-prod-minimum-32-bytes-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for Elder/Caretaker
    DOCTOR_SESSION_EXPIRE_MINUTES: int = 30  # Hard 30-min cap for Doctor QR/PIN session
    PIN_EXPIRE_MINUTES: int = 15             # 15-min TTL for generated 6-digit PIN

    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # External Services
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
