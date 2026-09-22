from __future__ import annotations
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # "http" fala com o serviço do docker-compose; "local" usa um diretório em
    # disco, dispensando Docker (útil em avaliação e CI).
    chroma_mode: str = os.getenv("CHROMA_MODE", "http")
    chroma_path: str = os.getenv("CHROMA_PATH", ".chroma")
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://rotulai:rotulai@localhost:5432/rotulai"
    )

    # Provedor do agent revisor: "gemini" ou "anthropic". Os dois usam o mesmo
    # prompt e o mesmo schema de saída, para que o provedor seja variável
    # controlada do experimento.
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")

    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-opus-5")

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))


settings = Settings()
