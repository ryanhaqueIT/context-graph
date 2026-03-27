"""SQLite-backed graph storage engine with BFS traversal and trajectory tracking."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections import deque
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

from context_graph.models.nodes import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)

_SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, node_type TEXT NOT NULL,"
    " name TEXT NOT NULL DEFAULT '', properties TEXT NOT NULL DEFAULT '{}',"
    " created_at TEXT NOT NULL, updated_at TEXT NOT NULL);"
    "CREATE TABLE IF NOT EXISTS edges (id TEXT PRIMARY KEY, edge_type TEXT NOT NULL,"
    " source_id TEXT NOT NULL REFERENCES nodes(id),"
    " target_id TEXT NOT NULL REFERENCES nodes(id),"
    " properties TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);"
    "CREATE TABLE IF NOT EXISTS trajectories (id TEXT PRIMARY KEY,"
    " agent_id TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,"
    " description TEXT NOT NULL DEFAULT '');"
    "CREATE TABLE IF NOT EXISTS trajectory_steps (id TEXT PRIMARY KEY,"
    " trajectory_id TEXT NOT NULL REFERENCES trajectories(id),"
    " step_order INTEGER NOT NULL, node_id TEXT NOT NULL REFERENCES nodes(id),"
    " action TEXT NOT NULL DEFAULT '', timestamp TEXT NOT NULL);"
)
_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);"
    "CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at);"
    "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);"
    "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);"
    "CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);"
    "CREATE INDEX IF NOT EXISTS idx_traj_steps_tid ON trajectory_steps(trajectory_id);"
    "CREATE INDEX IF NOT EXISTS idx_traj_steps_node ON trajectory_steps(node_id);"
)

_V6 = " VALUES (?,?,?,?,?,?)"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_node(row: sqlite3.Row) -> Node:
    return Node(
        id=row["id"],
        node_type=NodeType(row["node_type"]),
        name=row["name"],
        properties=json.loads(row["properties"]),
        created_at=row["created_at"],
    )


def _to_edge(row: sqlite3.Row) -> Edge:
    return Edge(
        id=row["id"],
        edge_type=EdgeType(row["edge_type"]),
        source_id=row["source_id"],
        target_id=row["target_id"],
        properties=json.loads(row["properties"]),
        created_at=row["created_at"],
    )


def _step_dict(s: sqlite3.Row) -> dict:
    return {"id": s["id"], "node_id": s["node_id"], "action": s["action"],
            "step_order": s["step_order"], "timestamp": s["timestamp"]}  # fmt: skip


class GraphStore:
    """SQLite-backed graph store with WAL mode for concurrent reads."""

    def __init__(self, db_path: Path, *, check_same_thread: bool = True) -> None:
        resolved = Path(db_path)
        if resolved.suffix != ".db":
            resolved = resolved / "graph.db"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = resolved
        self._check_same_thread = check_same_thread
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path), check_same_thread=self._check_same_thread
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _q(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._get_conn().execute(sql, params).fetchall()

    def _q1(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._get_conn().execute(sql, params).fetchone()

    def _ex(self, sql: str, params: tuple = ()) -> None:
        self._get_conn().execute(sql, params)
        self._get_conn().commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> GraphStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def initialize(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        conn.executescript(_INDEX_SQL)
        conn.commit()
        logger.info("Graph store initialized", extra={"path": str(self._db_path)})

    @property
    def is_initialized(self) -> bool:
        """True when the database file exists and has the nodes table."""
        if not self._db_path.exists():
            return False
        try:
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
            return self._q1(sql) is not None
        except sqlite3.DatabaseError:
            return False

    def add_node(self, node: Node) -> None:
        """Insert a node. Replaces if the id already exists."""
        p = json.dumps(node.properties)
        v = (node.id, node.node_type.value, node.name, p, node.created_at, _now())
        self._ex(
            "INSERT OR REPLACE INTO nodes (id,node_type,name,properties,created_at,updated_at)"
            + _V6,
            v,
        )

    def get_node(self, node_id: str) -> Node | None:
        r = self._q1("SELECT * FROM nodes WHERE id=?", (node_id,))
        return _to_node(r) if r else None

    def get_nodes_by_type(self, node_type: NodeType) -> list[Node]:
        rows = self._q("SELECT * FROM nodes WHERE node_type=?", (node_type.value,))
        return [_to_node(r) for r in rows]

    def get_nodes_by_name(self, name: str) -> list[Node]:
        rows = self._q("SELECT * FROM nodes WHERE name LIKE ?", (f"%{name}%",))
        return [_to_node(r) for r in rows]

    def find_nodes_by_property(
        self, key: str, value: str, node_type: NodeType | None = None
    ) -> list[Node]:
        if node_type is not None:
            rows = self._q(
                "SELECT * FROM nodes WHERE node_type=? AND json_extract(properties,'$.'||?) LIKE ?",
                (node_type.value, key, f"%{value}%"),
            )
        else:
            rows = self._q(
                "SELECT * FROM nodes WHERE json_extract(properties,'$.'||?) LIKE ?",
                (key, f"%{value}%"),
            )
        return [_to_node(r) for r in rows]

    def add_edge(self, edge: Edge) -> None:
        """Insert an edge. Replaces if the id already exists."""
        p = json.dumps(edge.properties)
        v = (edge.id, edge.edge_type.value, edge.source_id, edge.target_id, p, edge.created_at)
        self._ex(
            "INSERT OR REPLACE INTO edges (id,edge_type,source_id,target_id,properties,created_at)"
            + _V6,
            v,
        )

    def get_edges_from(self, source_id: str) -> list[Edge]:
        return [_to_edge(r) for r in self._q("SELECT * FROM edges WHERE source_id=?", (source_id,))]

    def get_edges_to(self, target_id: str) -> list[Edge]:
        return [_to_edge(r) for r in self._q("SELECT * FROM edges WHERE target_id=?", (target_id,))]

    def get_connected_nodes(self, node_id: str) -> list[Node]:
        rows = self._q(
            "SELECT DISTINCT n.* FROM nodes n JOIN edges e"
            " ON (e.target_id=n.id AND e.source_id=?)"
            " OR (e.source_id=n.id AND e.target_id=?)",
            (node_id, node_id),
        )
        return [_to_node(r) for r in rows]

    def traverse(
        self, start_id: str, edge_types: list[EdgeType] | None = None, max_depth: int = 3
    ) -> list[Node]:
        """BFS traversal from *start_id* up to *max_depth* hops."""
        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        result_ids: list[str] = []
        type_filter = {et.value for et in edge_types} if edge_types else None
        sql = "SELECT source_id,target_id,edge_type FROM edges WHERE source_id=? OR target_id=?"
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for row in self._q(sql, (current, current)):
                if type_filter and row["edge_type"] not in type_filter:
                    continue
                nb = row["target_id"] if row["source_id"] == current else row["source_id"]
                if nb not in visited:
                    visited.add(nb)
                    result_ids.append(nb)
                    queue.append((nb, depth + 1))
        return [n for nid in result_ids if (n := self.get_node(nid)) is not None]

    def find_paths(self, from_id: str, to_id: str, max_depth: int = 5) -> list[list[str]]:
        """Find all simple paths between two nodes via DFS, up to *max_depth*."""
        results: list[list[str]] = []
        stack: list[tuple[str, list[str]]] = [(from_id, [from_id])]
        sql = "SELECT source_id,target_id FROM edges WHERE source_id=? OR target_id=?"
        while stack:
            current, path = stack.pop()
            if current == to_id and len(path) > 1:
                results.append(path)
                continue
            if len(path) > max_depth:
                continue
            for row in self._q(sql, (current, current)):
                nb = row["target_id"] if row["source_id"] == current else row["source_id"]
                if nb not in path:
                    stack.append((nb, [*path, nb]))
        return results

    def start_trajectory(self, agent_id: str, description: str) -> str:
        """Start a new trajectory and return its id."""
        tid = str(uuid.uuid4())
        self._ex(
            "INSERT INTO trajectories (id,agent_id,started_at,description) VALUES (?,?,?,?)",
            (tid, agent_id, _now(), description),
        )
        logger.info("Trajectory started", extra={"trajectory_id": tid})
        return tid

    def record_step(self, trajectory_id: str, node_id: str, action: str) -> None:
        sql = "SELECT COALESCE(MAX(step_order),-1)+1 AS v"  # noqa: S608
        r = self._q1(sql + " FROM trajectory_steps WHERE trajectory_id=?", (trajectory_id,))
        v = (str(uuid.uuid4()), trajectory_id, r["v"], node_id, action, _now())  # type: ignore[index]
        self._ex(
            "INSERT INTO trajectory_steps (id,trajectory_id,step_order,node_id,action,timestamp)"
            + _V6,
            v,
        )

    def end_trajectory(self, trajectory_id: str) -> None:
        self._ex("UPDATE trajectories SET ended_at=? WHERE id=?", (_now(), trajectory_id))
        logger.info("Trajectory ended", extra={"trajectory_id": trajectory_id})

    def get_trajectory(self, trajectory_id: str) -> dict:
        """Return the full trajectory including its ordered steps."""
        t = self._q1("SELECT * FROM trajectories WHERE id=?", (trajectory_id,))
        if not t:
            return {}
        steps = self._q(
            "SELECT * FROM trajectory_steps WHERE trajectory_id=? ORDER BY step_order",
            (trajectory_id,),
        )
        return {
            "id": t["id"], "agent_id": t["agent_id"], "started_at": t["started_at"],
            "ended_at": t["ended_at"], "description": t["description"],
            "steps": [_step_dict(s) for s in steps],
        }  # fmt: skip

    def get_co_occurrence_stats(self) -> dict[str, int]:
        rows = self._q("SELECT trajectory_id,node_id FROM trajectory_steps ORDER BY trajectory_id")
        buckets: dict[str, list[str]] = {}
        for r in rows:
            buckets.setdefault(r["trajectory_id"], []).append(r["node_id"])
        counts: dict[str, int] = {}
        for nodes in buckets.values():
            for a, b in combinations(sorted(set(nodes)), 2):
                counts[f"{a}|{b}"] = counts.get(f"{a}|{b}", 0) + 1
        return counts

    @property
    def node_count(self) -> int:
        """Total number of nodes in the graph."""
        r = self._q1("SELECT COUNT(*) AS cnt FROM nodes")
        return r["cnt"] if r else 0  # type: ignore[index]

    @property
    def edge_count(self) -> int:
        """Total number of edges in the graph."""
        r = self._q1("SELECT COUNT(*) AS cnt FROM edges")
        return r["cnt"] if r else 0  # type: ignore[index]
