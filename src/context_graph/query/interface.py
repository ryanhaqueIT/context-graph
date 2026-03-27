"""Query interface for agents to interrogate the context graph.

Supports PlayerZero's 5 coordinate system joins:
1. Timeline joins (temporal)  2. Event joins (sequential)
3. Semantic joins (similarity) 4. Attribution joins (ownership)
5. Outcome joins (causal)
"""

from __future__ import annotations

import logging
from datetime import datetime

from context_graph.engine.store import GraphStore
from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    EdgeType,
    Node,
    NodeType,
)

logger = logging.getLogger(__name__)


class QueryInterface:
    """High-level query API for the context graph."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    # ── Timeline join (temporal) ─────────────────────

    def timeline(self, start_date: str, end_date: str) -> list[Node]:
        """All events in a time range. Accepts ISO-format date strings."""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        results: list[Node] = []
        for nt in (NodeType.CODE_CHANGE, NodeType.DECISION_TRACE, NodeType.INCIDENT):
            for node in self._store.get_nodes_by_type(nt):
                try:
                    node_dt = datetime.fromisoformat(node.created_at)
                except ValueError:
                    continue
                if start <= node_dt <= end:
                    results.append(node)
        results.sort(key=lambda n: n.created_at)
        return results

    def recent_changes(self, file_path: str | None = None, limit: int = 20) -> list[Node]:
        """Recent code changes, optionally filtered by file."""
        changes = self._store.get_nodes_by_type(NodeType.CODE_CHANGE)
        if file_path:
            file_nodes = self._store.find_nodes_by_property(
                "file_path", file_path, NodeType.CODE_UNIT
            )
            if not file_nodes:
                return []
            commit_ids: set[str] = set()
            for fn in file_nodes:
                for edge in self._store.get_edges_to(fn.id):
                    commit_ids.add(edge.source_id)
            changes = [c for c in changes if c.id in commit_ids]
        changes.sort(key=lambda n: n.created_at, reverse=True)
        return changes[:limit]

    # ── Event join (sequential) ──────────────────────

    def incidents_for_file(self, file_path: str) -> list[DecisionTrace]:
        """What broke near this code?"""
        traces = self._store.get_nodes_by_type(NodeType.DECISION_TRACE)
        results: list[DecisionTrace] = []
        for node in traces:
            if file_path in str(node.properties.get("files_affected", "")):
                results.append(DecisionTrace.from_node(node))
        results.sort(key=lambda t: t.created_at, reverse=True)
        return results

    def decisions_for_module(self, module_path: str) -> list[DecisionTrace]:
        """What decisions were made about this module?"""
        traces = self._store.get_nodes_by_type(NodeType.DECISION_TRACE)
        results: list[DecisionTrace] = []
        for node in traces:
            files_str = str(node.properties.get("files_affected", ""))
            files = files_str.split("|") if files_str else []
            if any(module_path in f for f in files):
                results.append(DecisionTrace.from_node(node))
        results.sort(key=lambda t: t.created_at, reverse=True)
        return results

    def fix_patterns(self, category: str | None = None) -> list[dict]:
        """Recurring fix patterns with frequency counts."""
        traces = self._store.get_nodes_by_type(NodeType.DECISION_TRACE)
        pattern_counts: dict[str, dict] = {}
        for node in traces:
            if str(node.properties.get("decision_type", "")) != DecisionType.BUG_FIX.value:
                continue
            categories_str = str(node.properties.get("categories", ""))
            cats = categories_str.split("|") if categories_str else []
            if category and category not in cats:
                continue
            for cat in cats:
                if cat not in pattern_counts:
                    pattern_counts[cat] = {"category": cat, "count": 0, "recent_fixes": []}
                pattern_counts[cat]["count"] += 1
                recent = pattern_counts[cat]["recent_fixes"]
                if len(recent) < 5:
                    trace = DecisionTrace.from_node(node)
                    recent.append(
                        {
                            "summary": trace.summary,
                            "rationale": trace.rationale,
                            "files": trace.files_affected,
                            "date": trace.created_at,
                        }
                    )
        return sorted(pattern_counts.values(), key=lambda p: p["count"], reverse=True)

    # ── Semantic join (similarity) ───────────────────

    def similar_incidents(self, description: str) -> list[DecisionTrace]:
        """Find incidents similar to a description via keyword overlap scoring."""
        keywords = set(description.lower().split())
        if not keywords:
            return []
        scored: list[tuple[float, DecisionTrace]] = []
        for node in self._store.get_nodes_by_type(NodeType.DECISION_TRACE):
            trace = DecisionTrace.from_node(node)
            corpus_words = set(f"{trace.summary} {trace.rationale}".lower().split())
            overlap = len(keywords & corpus_words)
            if overlap > 0:
                scored.append((overlap / len(keywords), trace))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [trace for _, trace in scored[:20]]

    # ── Attribution join (ownership) ─────────────────

    def knowledge_owners(self, file_path: str) -> list[dict]:
        """Who has the most context on this code? Combines commit authorship + traces."""
        author_scores: dict[str, dict] = {}
        for fn in self._store.find_nodes_by_property("file_path", file_path, NodeType.CODE_UNIT):
            for edge in self._store.get_edges_to(fn.id):
                commit = self._store.get_node(edge.source_id)
                if commit and commit.node_type == NodeType.CODE_CHANGE:
                    author = str(commit.properties.get("author", "unknown"))
                    if author not in author_scores:
                        author_scores[author] = {"author": author, "commits": 0, "traces": 0}
                    author_scores[author]["commits"] += 1
        for node in self._store.get_nodes_by_type(NodeType.DECISION_TRACE):
            if file_path in str(node.properties.get("files_affected", "")):
                actor = str(node.properties.get("actor", "unknown"))
                if actor not in author_scores:
                    author_scores[actor] = {"author": actor, "commits": 0, "traces": 0}
                author_scores[actor]["traces"] += 1
        owners = list(author_scores.values())
        for o in owners:
            o["score"] = o["commits"] + o["traces"] * 3
        owners.sort(key=lambda o: o["score"], reverse=True)
        return owners

    # ── Outcome join (causal) ────────────────────────

    def blast_radius(self, file_path: str) -> dict:
        """What could break if this file changes? Walks dependency + co-change edges."""
        file_nodes = self._store.find_nodes_by_property("file_path", file_path, NodeType.CODE_UNIT)
        dependents: list[str] = []
        co_changed: list[str] = []
        for fn in file_nodes:
            for edge in self._store.get_edges_to(fn.id):
                if edge.edge_type == EdgeType.DEPENDS_ON:
                    src = self._store.get_node(edge.source_id)
                    if src:
                        dependents.append(str(src.properties.get("file_path", src.name)))
            for edge in self._store.get_edges_to(fn.id):
                commit = self._store.get_node(edge.source_id)
                if commit and commit.node_type == NodeType.CODE_CHANGE:
                    for se in self._store.get_edges_from(commit.id):
                        sib = self._store.get_node(se.target_id)
                        if sib and sib.id != fn.id:
                            path = str(sib.properties.get("file_path", sib.name))
                            if path not in co_changed:
                                co_changed.append(path)
        incident_count = len(self.incidents_for_file(file_path))
        return {
            "file": file_path,
            "dependents": dependents,
            "co_changed_files": co_changed[:20],
            "historical_incidents": incident_count,
            "risk_score": len(dependents) + incident_count * 2,
        }

    def trace_causation(self, incident_id: str) -> dict:
        """Trace backward from incident to find likely cause via CAUSES/PRECEDED_BY edges."""
        node = self._store.get_node(incident_id)
        if not node:
            return {"error": "Incident not found", "id": incident_id}
        chain: list[dict] = [{"id": node.id, "name": node.name, "type": node.node_type.value}]
        visited: set[str] = {node.id}
        current_id = node.id
        for _ in range(10):
            found_cause = False
            for edge in self._store.get_edges_to(current_id):
                causal = edge.edge_type in (EdgeType.CAUSES, EdgeType.PRECEDED_BY)
                if causal and edge.source_id not in visited:
                    source = self._store.get_node(edge.source_id)
                    if source:
                        chain.append(
                            {
                                "id": source.id,
                                "name": source.name,
                                "type": source.node_type.value,
                                "relation": edge.edge_type.value,
                            }
                        )
                        visited.add(source.id)
                        current_id = source.id
                        found_cause = True
                        break
            if not found_cause:
                break
        return {"incident_id": incident_id, "causal_chain": chain}

    # ── Composite queries ────────────────────────────

    def what_if_change(self, file_path: str) -> dict:
        """Simulate 'what if I change this file?' combining blast_radius + incidents + patterns."""
        radius = self.blast_radius(file_path)
        incidents = self.incidents_for_file(file_path)
        categories: list[str] = []
        for t in incidents:
            categories.extend(t.categories)
        unique_cats = list(set(categories))
        relevant = [p for p in self.fix_patterns() if p["category"] in unique_cats]
        owners = self.knowledge_owners(file_path)
        return {
            "file": file_path,
            "blast_radius": radius,
            "historical_incidents": len(incidents),
            "recurring_categories": unique_cats,
            "relevant_patterns": relevant,
            "knowledge_owners": owners[:5],
            "risk_level": _risk_level(radius["risk_score"], len(incidents)),
        }

    def health_report(self) -> dict:
        """Graph coverage metrics."""
        code_units = self._store.get_nodes_by_type(NodeType.CODE_UNIT)
        traces = self._store.get_nodes_by_type(NodeType.DECISION_TRACE)
        changes = self._store.get_nodes_by_type(NodeType.CODE_CHANGE)
        files_with_traces: set[str] = set()
        for trace_node in traces:
            for f in str(trace_node.properties.get("files_affected", "")).split("|"):
                if f:
                    files_with_traces.add(f)
        all_file_paths = {
            str(n.properties.get("file_path", ""))
            for n in code_units
            if n.properties.get("file_path")
        }
        files_without_traces = all_file_paths - files_with_traces
        return {
            "total_nodes": self._store.node_count,
            "total_edges": self._store.edge_count,
            "code_units": len(code_units),
            "decision_traces": len(traces),
            "code_changes": len(changes),
            "files_with_traces": len(files_with_traces),
            "files_without_traces": len(files_without_traces),
            "coverage_ratio": (
                len(files_with_traces) / len(all_file_paths) if all_file_paths else 0.0
            ),
            "uncovered_files": sorted(files_without_traces)[:20],
        }


def _risk_level(risk_score: int, incident_count: int) -> str:
    """Classify risk as low/medium/high/critical."""
    if risk_score >= 10 or incident_count >= 5:
        return "critical"
    if risk_score >= 5 or incident_count >= 3:
        return "high"
    if risk_score >= 2 or incident_count >= 1:
        return "medium"
    return "low"
