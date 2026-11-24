from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.vectorstore import VectorStore
from ..models import Document


def seed_knowledge_base(db: Session, store: VectorStore, kb_dir: str) -> int:
    """Load every Markdown runbook in `kb_dir` that is not already indexed. Returns documents added."""
    base = Path(kb_dir)
    if not base.is_dir():
        return 0
    existing = set(db.scalars(select(Document.source)).all())
    added = 0
    for path in sorted(base.glob("*.md")):
        source = f"kb/{path.name}"
        if source in existing:
            continue
        text = path.read_text(encoding="utf-8")
        first = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
        store.add_document(first, text, source=source)
        added += 1
    return added
