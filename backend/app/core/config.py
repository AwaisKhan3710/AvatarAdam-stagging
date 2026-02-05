"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    PROJECT_NAME: str = "Avatar Adam"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database - use DATABASE_URL directly
    DATABASE_URL: str  # Format: postgresql+asyncpg://user:password@host:port/database

    # Security - JWT
    SECRET_KEY: str  # Generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = []

    # Database Connection Pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # Security
    BCRYPT_ROUNDS: int = 12

    # OpenRouter - LLM
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o"

    # ElevenLabs - Voice (TTS)
    ELEVENLABS_API_KEY: str = ""  # Required - set via environment variable
    ELEVENLABS_VOICE_ID: str = (
        "nPczCjzI2devNBz1zQrb"  # Brian - Deep, Resonant American male voice
    )
    ELEVENLABS_MODEL: str = "eleven_monolingual_v1"

    # OpenAI - Embeddings (via LangChain) and STT (Whisper)
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Pinecone - Vector Database
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "avatar-adam"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    # RAG Settings
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5

    # Mailgun Configuration
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = ""
    MAILGUN_FROM_EMAIL: str = ""
    MAILGUN_REGION: str = "US"
    MAILGUN_WEBHOOK_SIGNING_KEY: str = ""

    # Report Inaccuracy Settings
    REPORT_RECIPIENT_EMAIL: str = ""

    # HeyGen LiveAvatar
    HEYGEN_API_KEY: str = ""
    HEYGEN_AVATAR_ID: str = ""
    HEYGEN_API_URL: str = "https://api.liveavatar.com"
    HEYGEN_SANDBOX_MODE: bool = True  # Set to False for production

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
