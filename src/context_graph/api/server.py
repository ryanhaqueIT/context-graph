"""FastAPI application factory for the context graph API server."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from context_graph.api.routes import router


def create_app() -> FastAPI:
    """Build and return the FastAPI application with CORS and routes."""
    app = FastAPI(
        title="Context Graph API",
        description="API server exposing the context graph engine for frontend visualization",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
