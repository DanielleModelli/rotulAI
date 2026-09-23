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

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))


settings = Settings()
