"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

# Create limiter instance
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
    )


# Rate limit decorators for specific endpoints
# Usage: @limiter.limit("5/minute")
AUTH_LIMIT = "5/minute"  # Login/signup attempts
VOICE_LIMIT = "30/minute"  # Voice API calls (expensive)
CHAT_LIMIT = "60/minute"  # Chat API calls
UPLOAD_LIMIT = "10/minute"  # File uploads
