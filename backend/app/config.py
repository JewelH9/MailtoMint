from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    app_env: str = "development"
    allowed_origins: str = "http://localhost:5173"
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]
    
    imap_email: str = ""
    imap_password: str = ""
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    email_poll_interval: int = 300
    allowed_hosts: str = "localhost,127.0.0.1"


@lru_cache()
def get_settings() -> Settings:
    return Settings()