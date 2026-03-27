"""Configuration loading for context graph.

All environment variable access is centralized here.
No other module may import os.environ or os.getenv.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Default graph store location (relative to repo root)
DEFAULT_GRAPH_DIR = ".harness/context-graph"

# Maximum nodes before compaction warning
MAX_NODES_BEFORE_WARNING = 100_000


def get_graph_dir(override: str | None = None) -> Path:
    """Return the path to the context graph store directory."""
    if override:
        return Path(override)
    env_val = os.environ.get("CONTEXT_GRAPH_DIR")
    if env_val:
        return Path(env_val)
    return Path.cwd() / DEFAULT_GRAPH_DIR


def get_repo_root() -> Path:
    """Detect the git repository root, or fall back to cwd."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
    return cwd


def get_log_level() -> int:
    """Return configured log level."""
    level = os.environ.get("CONTEXT_GRAPH_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)
