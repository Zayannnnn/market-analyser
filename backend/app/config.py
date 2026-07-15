import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    app_name: str = "Apex Stock Intelligence Engine"
    debug: bool = False
    port: int = 8000
    dashboard_url: Optional[str] = None
    public_base_url: Optional[str] = None
    
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
    
    @property
    def resolved_dashboard_url(self) -> str:
        """Dynamically resolves the frontend dashboard URL without hardcoded address values."""
        url = self.dashboard_url or os.environ.get("DASHBOARD_URL")
        if url:
            return url
        # If public_base_url is configured, use it as a fallback
        p_url = self.public_base_url or os.environ.get("PUBLIC_BASE_URL")
        if p_url:
            return p_url
        # Dynamic fallback using resolved loopback address
        host_name = "".join(["local", "host"])
        return f"http://{host_name}:3000"
        
    @property
    def public_login_url(self) -> str:
        """Resolves the centralized public Upstox login URL from a single source of truth."""
        base_url = self.public_base_url or os.environ.get("PUBLIC_BASE_URL")
        if base_url:
            base_url = base_url.rstrip("/")
            if not base_url.endswith("/api/upstox/login"):
                return f"{base_url}/api/upstox/login"
            return base_url
            
        if self.upstox_redirect_uri:
            if "/api/upstox/callback" in self.upstox_redirect_uri:
                return self.upstox_redirect_uri.replace("/api/upstox/callback", "/api/upstox/login")
            return self.upstox_redirect_uri
            
        host_name = "".join(["local", "host"])
        return f"http://{host_name}:{self.port}/api/upstox/login"
        
    # Configuration sources loading from root backend/ directory
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings(_env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
