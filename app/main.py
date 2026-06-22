"""Nyaykosh FastAPI backend.

Serves the data + logic that the Next.js frontend (dpdp/) originally bundled
client-side: laws catalog, public laws API, compliance simulator, admin auth,
and admin CRUD / rule import.
"""
from __future__ import annotations

from copy import deepcopy

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

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


# --- Laws-only Swagger view -----------------------------------------------
# A dedicated docs page that exposes ONLY the public laws endpoints and hides
# the schemas/models section. Linked from the "Access this law" panel.

@app.get("/laws-openapi.json", include_in_schema=False)
def laws_openapi() -> JSONResponse:
    """OpenAPI spec filtered to the public laws endpoints, with schemas removed."""
    full = app.openapi()
    spec = deepcopy(full)

    # Keep only public GET /laws paths (drop admin + everything else).
    spec["paths"] = {
        path: methods
        for path, methods in full.get("paths", {}).items()
        if path.startswith(f"{_prefix}/laws") and "admin" not in path
    }

    # Drop the schemas/models section so Swagger shows no "Schemas" block.
    spec.pop("components", None)
    # Inline $ref-free responses: strip any leftover schema refs the UI would
    # try to resolve against the now-removed components.
    for methods in spec["paths"].values():
        for op in methods.values():
            for resp in op.get("responses", {}).values():
                resp.pop("content", None)

    spec["tags"] = [{"name": "laws"}]
    spec["info"] = {**spec.get("info", {}), "title": "Nyaykosh — Laws REST API"}
    return JSONResponse(spec)


@app.get("/laws-docs", include_in_schema=False)
def laws_docs():
    """Swagger UI bound to the laws-only spec (no schemas)."""
    return get_swagger_ui_html(
        openapi_url="/laws-openapi.json",
        title="Nyaykosh — Laws REST API",
    )


_prefix = settings.api_v1_prefix
app.include_router(auth.router, prefix=_prefix)
app.include_router(laws.router, prefix=_prefix)
app.include_router(simulator.router, prefix=_prefix)
app.include_router(content.router, prefix=_prefix)
app.include_router(admin.router, prefix=_prefix)
