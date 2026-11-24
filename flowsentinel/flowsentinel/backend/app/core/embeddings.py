"""Embedding backends.

`HashingEmbeddings` is a deterministic, dependency-free embedder (hashing trick over
stemmed unigrams + bigrams). It lets the whole RAG pipeline run offline and in tests.
When an OpenAI key is configured, `get_embeddings()` returns LangChain's OpenAIEmbeddings
truncated to the same dimension so the pgvector column does not change.
"""
from __future__ import annotations

import hashlib
import math
import re

try:  # keep this module importable without LangChain installed
    from langchain_core.embeddings import Embeddings as _Base
except ImportError:  # pragma: no cover
    class _Base:  # type: ignore[no-redef]
        pass

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_\-\.]*[a-z0-9]|[a-z0-9]")
_STOP = frozenset(
    "a an and are as at be by for from has have i in is it its of on or that the this to was were will with "
    "my our we you your not no can cant cannot could do does did am been being if then so than too very just "
    "please help hi hello thanks every minute minutes since morning today yesterday again keep keeps get gets "
    "roughly need needs want some any all also still now when what which who how why there here".split()
)
_SUFFIXES = ("ations", "ation", "ings", "ing", "edly", "ed", "ies", "es", "s")


def _stem(tok: str) -> str:
    for suf in _SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)]
    return tok


def tokenize(text: str) -> list[str]:
    toks = [t.strip(".-_") for t in _TOKEN.findall(text.lower())]
    # drop stop-words and 1-2 digit numbers ("10 minutes" carries no topical signal)
    return [_stem(t) for t in toks if t and t not in _STOP and not (t.isdigit() and len(t) < 3)]


class HashingEmbeddings(_Base):
    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _bucket(self, feature: str) -> tuple[int, float]:
        h = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        n = int.from_bytes(h, "big")
        return n % self.dim, (1.0 if (n >> 63) & 1 else -1.0)

    def embed_query(self, text: str) -> list[float]:
        toks = tokenize(text)
        feats: dict[str, float] = {}
        for t in toks:
            feats[t] = feats.get(t, 0.0) + 1.0
        for a, b in zip(toks, toks[1:]):
            key = f"{a}_{b}"
            feats[key] = feats.get(key, 0.0) + 1.0
        vec = [0.0] * self.dim
        for f, tf in feats.items():
            idx, sign = self._bucket(f)
            weight = (1.0 + math.log(tf)) * (1.4 if "_" in f else 1.0)
            vec[idx] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]


def get_embeddings(settings):
    provider = settings.embedding_provider
    use_openai = provider == "openai" or (provider == "auto" and settings.openai_api_key)
    if use_openai and settings.openai_api_key:
        try:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
                dimensions=settings.embedding_dim,
            )
        except Exception:  # pragma: no cover - falls back to offline embeddings
            pass
    return HashingEmbeddings(settings.embedding_dim)
