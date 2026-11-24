"""Vector store over the `chunks` table.

PostgreSQL  -> pgvector cosine search (`<=>`) with an HNSW index.
Other (SQLite dev/tests) -> exact cosine search with numpy.
Vectors are L2-normalised by the embedders, so cosine similarity == dot product.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import Chunk, Document
from .chunking import chunk_markdown


class VectorStore:
    def __init__(self, db: Session, embeddings, chunk_chars: int = 900, chunk_overlap: int = 120):
        self.db = db
        self.embeddings = embeddings
        self.chunk_chars = chunk_chars
        self.chunk_overlap = chunk_overlap

    # ---- ingestion -------------------------------------------------------------
    def add_document(self, title: str, content: str, source: str = "manual") -> Document:
        doc = Document(title=title.strip(), content=content, source=source)
        self.db.add(doc)
        self.db.flush()
        self._index(doc)
        self.db.commit()
        return doc

    def _index(self, doc: Document) -> int:
        pieces = chunk_markdown(doc.content, self.chunk_chars, self.chunk_overlap)
        if not pieces:
            return 0
        texts = [f"{doc.title}\n{p.heading}\n{p.text}" for p in pieces]
        vectors = self.embeddings.embed_documents(texts)
        for i, (p, v) in enumerate(zip(pieces, vectors)):
            self.db.add(Chunk(document_id=doc.id, ordinal=i, heading=p.heading, content=p.text, embedding=list(v)))
        return len(pieces)

    def reindex_all(self) -> int:
        """Re-embed every document (needed after switching embedding provider)."""
        self.db.query(Chunk).delete()
        total = 0
        for doc in self.db.scalars(select(Document)).all():
            total += self._index(doc)
        self.db.commit()
        return total

    # ---- retrieval -------------------------------------------------------------
    def search(self, query: str, k: int = 4, min_score: float = 0.0) -> list[dict]:
        qvec = self.embeddings.embed_query(query)
        if self.db.bind.dialect.name == "postgresql":
            rows = self._search_pg(qvec, k)
        else:
            rows = self._search_numpy(qvec, k)
        rows = [(cid, s) for cid, s in rows if s >= min_score]
        if not rows:
            return []
        chunks = {c.id: c for c in self.db.scalars(select(Chunk).where(Chunk.id.in_([cid for cid, _ in rows])))}
        titles = {d.id: d.title for d in self.db.scalars(
            select(Document).where(Document.id.in_({c.document_id for c in chunks.values()})))}
        return [
            {
                "chunk_id": cid,
                "document_id": chunks[cid].document_id,
                "title": titles.get(chunks[cid].document_id, ""),
                "heading": chunks[cid].heading,
                "content": chunks[cid].content,
                "score": round(float(score), 4),
            }
            for cid, score in rows
            if cid in chunks
        ]

    def _search_pg(self, qvec: list[float], k: int) -> list[tuple[int, float]]:
        literal = "[" + ",".join(f"{x:.6f}" for x in qvec) + "]"
        rows = self.db.execute(
            text(
                "SELECT id, 1 - (embedding <=> CAST(:q AS vector)) AS score FROM chunks "
                "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
            ),
            {"q": literal, "k": k},
        ).all()
        return [(r[0], float(r[1])) for r in rows]

    def _search_numpy(self, qvec: list[float], k: int) -> list[tuple[int, float]]:
        rows = self.db.execute(select(Chunk.id, Chunk.embedding)).all()
        if not rows:
            return []
        ids = [r[0] for r in rows]
        mat = np.array([r[1] for r in rows], dtype=np.float32)
        scores = mat @ np.array(qvec, dtype=np.float32)
        order = np.argsort(-scores)[:k]
        return [(ids[i], float(scores[i])) for i in order]
