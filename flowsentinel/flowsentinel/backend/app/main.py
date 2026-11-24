import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analytics, incidents, knowledge
from .config import get_settings
from .db import SessionLocal, engine, init_db
from .services.ingestion import seed_knowledge_base
from .services.runtime import get_runtime, make_store

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.auto_seed:
        with SessionLocal() as db:
            added = seed_knowledge_base(db, make_store(db), settings.kb_dir)
            if added:
                logging.getLogger("flowsentinel").info("Seeded %d knowledge-base documents", added)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(incidents.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)


@app.get("/api/health", tags=["health"])
def health():
    rt = get_runtime()
    return {
        "status": "ok",
        "database": engine.dialect.name,
        "llm": "enabled" if rt.llm else "offline (rules + extractive answers)",
        "embeddings": type(rt.embeddings).__name__,
    }
