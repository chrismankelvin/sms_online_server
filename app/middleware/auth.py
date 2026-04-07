from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
import logging
from app.config.settings import settings
import os

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the API key from the Authorization header.
    Expected format: Authorization: Bearer <api_key>
    """
    if not credentials:
        logger.warning("No API key provided in request")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required. Use: Authorization: Bearer <your-api-key>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    if api_key not in settings.api_keys_list:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    logger.debug(f"API key verified successfully")
    return api_key

# Optional: Rate limiting by API key instead of IP
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.disabled = os.getenv("DISABLE_RATE_LIMITING", "false").lower() == "true"  # ← ADD
    
    def is_allowed(self, api_key: str, limit: int, window_seconds: int) -> bool:
        # ← ADD THIS BLOCK
        if self.disabled:
            return True
        
        import time
        now = time.time()
        
        if api_key not in self.requests:
            self.requests[api_key] = []
        
        cutoff = now - window_seconds
        self.requests[api_key] = [ts for ts in self.requests[api_key] if ts > cutoff]
        
        if len(self.requests[api_key]) >= limit:
            return False
        
        self.requests[api_key].append(now)
        return True
rate_limiter = RateLimiter()