from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'recipe_extractor.db'}",
    )
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    use_llm: bool = _env_bool("USE_LLM", True)
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "18"))
    max_scraped_chars: int = int(os.getenv("MAX_SCRAPED_CHARS", "14000"))
    prompts_dir: Path = BASE_DIR / "prompts"
    frontend_dir: Path = BASE_DIR / "frontend"


settings = Settings()
