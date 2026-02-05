"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.middleware.rate_limit import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    try:
        # Initialize database (create tables if they don't exist)
        # In production, use Alembic migrations instead
        if settings.DEBUG:
            print(
                "⚠️  Skipping database initialization - start PostgreSQL and run migrations manually"
            )
            # await init_db()
    except Exception as e:
        print(f"Error during startup: {e}")
        raise

    yield

    # Shutdown
    try:
        await close_db()
    except Exception as e:
        print(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent 307 redirects that lose auth headers
)

# Configure CORS - use specific origins for security
# When BACKEND_CORS_ORIGINS is empty, allow localhost for development only
cors_origins = (
    settings.BACKEND_CORS_ORIGINS
    if settings.BACKEND_CORS_ORIGINS
    else [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Avatar Adam API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
