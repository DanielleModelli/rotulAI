from __future__ import annotations
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://rotulai:rotulai@localhost:5432/rotulai"
    )

    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-opus-5")

    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))


settings = Settings()
