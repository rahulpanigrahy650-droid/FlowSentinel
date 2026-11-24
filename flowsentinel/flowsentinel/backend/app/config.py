from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FlowSentinel"
    # Postgres in docker-compose; SQLite keeps local dev/tests dependency-free.
    database_url: str = "sqlite:///./flowsentinel.db"

    # LLM: "auto" picks Anthropic, then OpenAI, based on which key is present.
    # "none" forces the offline path (rules + extractive answers).
    llm_provider: str = "auto"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Embeddings: "auto" uses OpenAI embeddings when a key exists, else the offline hashing embedder.
    embedding_provider: str = "auto"
    embedding_dim: int = 1024

    # Retrieval / routing thresholds
    top_k: int = 4
    # Tuned for the offline hashing embedder (cosine scores are low in absolute terms).
    # With OpenAI embeddings use roughly MIN_SCORE=0.30 and AUTO_SCORE=0.45.
    min_score: float = 0.10      # below this a passage is not considered relevant
    auto_score: float = 0.20     # best score needed to mark a suggestion as "confident"
    chunk_chars: int = 900
    chunk_overlap: int = 120

    kb_dir: str = str(BASE_DIR / "knowledge_base")
    auto_seed: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
