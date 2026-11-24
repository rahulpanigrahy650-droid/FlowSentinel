from pathlib import PurePath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Chunk, Document
from ..schemas import DocumentCreate, DocumentOut, PassageOut, SearchIn
from ..services.runtime import make_store

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

MAX_UPLOAD_BYTES = 1_000_000


def _out(db: Session, doc: Document) -> DocumentOut:
    n = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)) or 0
    return DocumentOut(id=doc.id, title=doc.title, source=doc.source, created_at=doc.created_at, chunk_count=n)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Chunk.document_id, func.count()).group_by(Chunk.document_id)).all())
    docs = db.scalars(select(Document).order_by(Document.created_at.desc(), Document.id.desc())).all()
    return [DocumentOut(id=d.id, title=d.title, source=d.source, created_at=d.created_at,
                        chunk_count=counts.get(d.id, 0)) for d in docs]


@router.post("/documents", response_model=DocumentOut, status_code=201)
def add_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    return _out(db, make_store(db).add_document(payload.title, payload.content, payload.source))


@router.post("/documents/upload", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 1 MB)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "Only UTF-8 text or Markdown files are supported")
    if len(text.strip()) < 20:
        raise HTTPException(400, "File is empty or too short")
    name = PurePath(file.filename or "upload").stem
    return _out(db, make_store(db).add_document(name, text, source=f"upload/{file.filename}"))


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()


@router.post("/search", response_model=list[PassageOut])
def search(body: SearchIn, db: Session = Depends(get_db)):
    return make_store(db).search(body.query, body.k)


@router.post("/reindex")
def reindex(db: Session = Depends(get_db)):
    """Re-embed all documents (run after changing EMBEDDING_PROVIDER / dimension)."""
    return {"chunks": make_store(db).reindex_all()}
