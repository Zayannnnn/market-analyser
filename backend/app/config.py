import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    app_name: str = "Apex Stock Intelligence Engine"
    debug: bool = False
    port: int = 8000
    dashboard_url: str = "http://localhost:3000"
    
    # Gemini API
    gemini_api_key: str
    
    # Firebase settings
    firebase_service_account_path: Optional[str] = None
    
    # Upstox API settings
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_redirect_uri: Optional[str] = None
    
    # Telegram Bot Alert Settings
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Cache settings
    cache_expiry_seconds: int = 900  # 15 minutes cache default
    
    # Rate limit alerts
    max_alerts_per_day: int = 10
    
    # Configuration sources loading from root backend/ directory
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings(_env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
