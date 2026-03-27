"""Dependency injection for the FastAPI API layer.

Provides a singleton GraphStore that is lazily initialized on first request.
Uses check_same_thread=False because FastAPI runs handlers in a thread pool.
"""

from __future__ import annotations

from context_graph.config.settings import get_graph_dir
from context_graph.engine.store import GraphStore

_store: GraphStore | None = None


def get_store() -> GraphStore:
    """Return the shared GraphStore singleton, initializing it on first call."""
    global _store
    if _store is None:
        _store = GraphStore(get_graph_dir(), check_same_thread=False)
        _store.initialize()
    return _store


def override_store(store: GraphStore) -> None:
    """Override the global store (used in tests)."""
    global _store
    _store = store


def reset_store() -> None:
    """Reset the global store to None (used in tests)."""
    global _store
    _store = None
