from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Catalyst ElderCare Platform"
    ENVIRONMENT: str = "development"

    JWT_SECRET_KEY: str = "dev-secret-key-change-in-prod-minimum-32-bytes-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DOCTOR_SESSION_EXPIRE_MINUTES: int = 30
    PIN_EXPIRE_MINUTES: int = 15

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""

    # Email Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()