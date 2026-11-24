import math
from pathlib import Path

import pytest

from app.core.chunking import chunk_markdown
from app.core.embeddings import HashingEmbeddings

KB = Path(__file__).resolve().parent.parent / "knowledge_base"


class InMemoryRetriever:
    """Same retrieval maths as VectorStore._search_numpy, without any database."""

    def __init__(self):
        self.emb = HashingEmbeddings(1024)
        self.items = []
        for path in sorted(KB.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = next(ln[2:].strip() for ln in text.splitlines() if ln.startswith("# "))
            for c in chunk_markdown(text):
                vec = self.emb.embed_query(f"{title}\n{c.heading}\n{c.text}")
                self.items.append({"title": title, "heading": c.heading, "content": c.text, "vec": vec})

    def __call__(self, query: str, k: int):
        q = self.emb.embed_query(query)
        scored = sorted(((sum(a * b for a, b in zip(q, it["vec"])), it) for it in self.items), key=lambda x: -x[0])
        return [{"chunk_id": i, "document_id": 0, "title": it["title"], "heading": it["heading"],
                 "content": it["content"], "score": round(s, 4)} for i, (s, it) in enumerate(scored[:k])]


@pytest.fixture(scope="session")
def retriever():
    return InMemoryRetriever()
