"""Ingest git history into the context graph with diff stats and blame."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from context_graph.config.settings import get_repo_root
from context_graph.engine.store import GraphStore
from context_graph.models.nodes import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)

# Delimiter unlikely to appear in commit messages.
_FIELD_SEP = "<%SEP%>"
# Git log format: hash, author, date, parent hashes, subject.
_LOG_FORMAT = _FIELD_SEP.join(["%H", "%an", "%aI", "%P", "%s"])


class GitIngestor:
    """Robust git history ingestion with diff stats and blame support."""

    def __init__(self, store: GraphStore, repo_root: Path | None = None) -> None:
        self._store = store
        self._repo_root = (repo_root or get_repo_root()).resolve()

    def ingest_history(self, max_commits: int = 500) -> dict:
        """Ingest commit history. Returns ``{commits_added, edges_created}``."""
        raw_log = self._run_git_log(max_commits)
        if raw_log is None:
            return {"commits_added": 0, "edges_created": 0, "error": True}

        commits = self._parse_log(raw_log)
        commits_added = 0
        edges_created = 0
        prev_node: Node | None = None

        for commit in commits:
            # --- upsert commit node ---
            existing = self._store.find_nodes_by_property(
                "commit_hash",
                commit["hash"],
                NodeType.CODE_CHANGE,
            )
            if existing:
                node = existing[0]
            else:
                node = Node(
                    node_type=NodeType.CODE_CHANGE,
                    name=commit["subject"][:200] if commit["subject"] else "(empty)",
                    properties={
                        "commit_hash": commit["hash"],
                        "author": commit["author"],
                        "date": commit["date"],
                        "message": commit["subject"],
                        "parent_hashes": commit["parents"],
                        "is_merge": len(commit["parents"].split()) > 1,
                    },
                )
                self._store.add_node(node)
                commits_added += 1

            # --- diff stats for each file ---
            for fstat in commit.get("file_stats", []):
                file_node = self._ensure_file_node(fstat["path"])
                edge = Edge(
                    edge_type=EdgeType.MODIFIES,
                    source_id=node.id,
                    target_id=file_node.id,
                    properties={
                        "lines_added": fstat["added"],
                        "lines_deleted": fstat["deleted"],
                    },
                )
                self._store.add_edge(edge)
                edges_created += 1

            # --- temporal ordering ---
            if prev_node is not None:
                temporal = Edge(
                    edge_type=EdgeType.PRECEDED_BY,
                    source_id=prev_node.id,
                    target_id=node.id,
                    properties={"relationship": "temporal_order"},
                )
                self._store.add_edge(temporal)
                edges_created += 1

            prev_node = node

        summary = {
            "commits_added": commits_added,
            "edges_created": edges_created,
        }
        logger.info("Git history ingested", extra=summary)
        return summary

    def get_file_ownership(self, file_path: str) -> dict[str, int]:
        """Return ``{author: line_count}`` via git blame."""
        abs_path = self._repo_root / file_path
        if not abs_path.exists():
            logger.warning("File not found for blame", extra={"path": file_path})
            return {}

        result = self._run_git(
            ["git", "blame", "--porcelain", "--", file_path],
        )
        if result is None:
            return {}

        ownership: dict[str, int] = {}
        for line in result.splitlines():
            if line.startswith("author "):
                author = line[len("author ") :].strip()
                ownership[author] = ownership.get(author, 0) + 1

        logger.debug(
            "Blame computed",
            extra={
                "path": file_path,
                "authors": len(ownership),
            },
        )
        return ownership

    def get_commit_files(self, commit_hash: str) -> list[dict]:
        """Return files changed in a commit: ``[{path, added, deleted}]``."""
        result = self._run_git(
            [
                "git",
                "diff-tree",
                "--no-commit-id",
                "-r",
                "--numstat",
                "--diff-filter=ACDMRT",
                commit_hash,
            ]
        )
        if result is None:
            return []

        files: list[dict] = []
        for line in result.strip().splitlines():
            parts = line.split("\t", maxsplit=2)
            if len(parts) < 3:
                continue
            added_str, deleted_str, path = parts
            files.append(
                {
                    "path": path.strip(),
                    "added": _safe_int(added_str),
                    "deleted": _safe_int(deleted_str),
                }
            )
        return files

    def _run_git(self, cmd: list[str]) -> str | None:
        """Run a git command and return stdout, or None on failure."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self._repo_root),
                timeout=60,
            )
        except FileNotFoundError:
            logger.error("git binary not found")
            return None
        except subprocess.TimeoutExpired:
            logger.error("git command timed out", extra={"cmd": cmd[:3]})
            return None

        if result.returncode != 0:
            logger.warning(
                "git command failed",
                extra={
                    "cmd": " ".join(cmd[:4]),
                    "stderr": result.stderr[:300] if result.stderr else "",
                },
            )
            return None
        return result.stdout

    def _run_git_log(self, max_commits: int) -> str | None:
        """Retrieve git log with numstat diff information."""
        return self._run_git(
            [
                "git",
                "log",
                f"--max-count={max_commits}",
                f"--pretty=format:{_LOG_FORMAT}",
                "--numstat",
            ]
        )

    def _parse_log(self, raw: str) -> list[dict]:
        """Parse git-log + numstat output into structured dicts."""
        commits: list[dict] = []
        current: dict | None = None

        for line in raw.splitlines():
            # Try to detect a commit header line.
            if _FIELD_SEP in line:
                # Flush previous commit.
                if current is not None:
                    commits.append(current)

                parts = line.split(_FIELD_SEP, maxsplit=4)
                if len(parts) < 5:
                    # Malformed line -- skip.
                    logger.debug("Skipping malformed log line", extra={"line": line[:120]})
                    current = None
                    continue

                commit_hash, author, date, parents, subject = parts
                current = {
                    "hash": commit_hash.strip(),
                    "author": author.strip(),
                    "date": date.strip(),
                    "parents": parents.strip(),
                    "subject": subject.strip(),
                    "file_stats": [],
                }
                continue

            # Numstat lines: ``added\tdeleted\tpath``
            stripped = line.strip()
            if not stripped:
                continue

            if current is not None:
                match = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", stripped)
                if match:
                    current["file_stats"].append(
                        {
                            "path": match.group(3).strip(),
                            "added": _safe_int(match.group(1)),
                            "deleted": _safe_int(match.group(2)),
                        }
                    )

        # Flush last commit.
        if current is not None:
            commits.append(current)

        logger.debug("Parsed commits", extra={"count": len(commits)})
        return commits

    def _ensure_file_node(self, file_path: str) -> Node:
        """Find or create a CODE_UNIT node for a file path."""
        existing = self._store.find_nodes_by_property(
            "file_path",
            file_path,
            NodeType.CODE_UNIT,
        )
        if existing:
            return existing[0]

        node = Node(
            node_type=NodeType.CODE_UNIT,
            name=file_path,
            properties={"file_path": file_path},
        )
        self._store.add_node(node)
        return node


def _safe_int(value: str) -> int:
    """Convert a numstat field to int; binary diffs use ``-``."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def ingest_git_history(store: GraphStore, max_commits: int = 500) -> int:
    """Legacy entry-point -- delegates to ``GitIngestor``.

    Returns the number of commits ingested.
    """
    ingestor = GitIngestor(store)
    summary = ingestor.ingest_history(max_commits)
    return summary.get("commits_added", 0)
