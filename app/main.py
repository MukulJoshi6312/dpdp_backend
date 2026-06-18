"""Nyaykosh FastAPI backend.

Serves the data + logic that the Next.js frontend (dpdp/) originally bundled
client-side: laws catalog, public laws API, compliance simulator, admin auth,
and admin CRUD / rule import.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.api import admin, auth, content, laws, simulator
from app.core.config import settings
from app.core.database import Base, engine
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure schema exists and base data is present on startup.
    Base.metadata.create_all(bind=engine)
    seed()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="1.0.0",
    description="Open-access API for Indian laws + compliance simulator (Nyaykosh).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


_prefix = settings.api_v1_prefix
app.include_router(auth.router, prefix=_prefix)
app.include_router(laws.router, prefix=_prefix)
app.include_router(simulator.router, prefix=_prefix)
app.include_router(content.router, prefix=_prefix)
app.include_router(admin.router, prefix=_prefix)
