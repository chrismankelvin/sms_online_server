import os
from typing import List

class Settings:
    # Server
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 8001))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # Database
    SQLITECLOUD_CONNECTION_STRING = os.getenv("SQLITECLOUD_CONNECTION_STRING")
    if not SQLITECLOUD_CONNECTION_STRING:
        raise ValueError("SQLITECLOUD_CONNECTION_STRING is required")
    
    # Security - NO DEFAULTS!
    RECOVERY_SECRET = os.getenv("RECOVERY_SECRET")
    if not RECOVERY_SECRET:
        raise ValueError("RECOVERY_SECRET is required")
    
    # API Keys - comma separated list
    VALID_API_KEYS = os.getenv("RECOVERY_API_KEYS", "")
    if not VALID_API_KEYS:
        raise ValueError("RECOVERY_API_KEYS is required (comma-separated list)")
    
    # Convert to list
    @property
    def api_keys_list(self) -> List[str]:
        return [key.strip() for key in self.VALID_API_KEYS.split(",") if key.strip()]
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:3000"]')
    
    @property
    def cors_origins_list(self) -> list:
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["http://localhost:5173", "http://localhost:3000"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "60"))
    RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "100"))

settings = Settings()