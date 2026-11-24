"""Process-wide singletons: settings, embedding backend and (optional) LLM adapter."""
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..core.embeddings import get_embeddings
from ..core.llm import LLMAdapter, get_llm
from ..core.vectorstore import VectorStore


@dataclass
class Runtime:
    settings: Settings
    embeddings: object
    llm: LLMAdapter | None


@lru_cache
def get_runtime() -> Runtime:
    s = get_settings()
    return Runtime(settings=s, embeddings=get_embeddings(s), llm=get_llm(s))


def make_store(db: Session) -> VectorStore:
    rt = get_runtime()
    return VectorStore(db, rt.embeddings, rt.settings.chunk_chars, rt.settings.chunk_overlap)
