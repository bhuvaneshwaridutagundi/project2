
import os
from dotenv import load_dotenv

load_dotenv(override=False)


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "dev-key-change-me"
    )

    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", "instance/gateway.db"
    )

    MAX_CONTENT_LENGTH = (
        int(os.environ.get("MAX_CONTENT_LENGTH_MB", 10))
        * 1024 * 1024
    )

    # Security thresholds
    ALLOW_THRESHOLD = 29
    FLAG_THRESHOLD = 69

    # LLM configuration
    LLM_PROVIDER = os.environ.get(
        "LLM_PROVIDER", "none"
    ).strip().lower()

    GEMINI_API_KEY = os.environ.get(
        "GEMINI_API_KEY", ""
    ).strip()

    GEMINI_MODEL = os.environ.get(
        "GEMINI_MODEL", "gemini-2.5-flash"
    ).strip()

    LLM_API_KEY = os.environ.get(
        "LLM_API_KEY", ""
    ).strip()

    LLM_MODEL = os.environ.get(
        "LLM_MODEL", "gemini-2.5-flash"
    ).strip()

    # LLM health status
    LLM_CONFIGURED = (
        LLM_PROVIDER == "gemini"
        and bool(GEMINI_API_KEY)
    )
