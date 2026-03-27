"""Simulation engine for "what if?" queries.

This is the module that makes the context graph more than a search index.
It answers: "What happens if I change this file?" by combining:
  1. Dependency graph (blast radius)
  2. Historical incident data (what broke before)
  3. Fix patterns (how similar issues were resolved)
  4. Attribution data (who knows about this code)
  5. Temporal data (recent changes that could interact)

This is NOT ML-based simulation like PlayerZero's Sim-1.
It is graph-based impact analysis + historical pattern matching.
Think of it as: the graph-traversal part of what Sim-1 does,
without the neural code simulation.

To get closer to Sim-1, feed the output of these queries to Claude
as context for code-level behavioral simulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from context_graph.engine.store import GraphStore
from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """A single risk factor identified by simulation."""

    category: str
    severity: str  # "high", "medium", "low"
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SimulationResult:
    """Complete result of a 'what if?' simulation."""

    file_path: str
    overall_risk: str  # "high", "medium", "low"
    confidence: float
    blast_radius: dict = field(default_factory=dict)
    historical_incidents: list[dict] = field(default_factory=list)
    recurring_patterns: list[dict] = field(default_factory=list)
    risk_factors: list[RiskFactor] = field(default_factory=list)
    knowledge_owners: list[dict] = field(default_factory=list)
    recent_activity: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    simulation_context: str = ""  # Markdown context for feeding to Claude

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "file_path": self.file_path,
            "overall_risk": self.overall_risk,
            "confidence": self.confidence,
            "blast_radius": self.blast_radius,
            "historical_incidents": self.historical_incidents,
            "recurring_patterns": self.recurring_patterns,
            "risk_factors": [
                {
                    "category": rf.category,
                    "severity": rf.severity,
                    "description": rf.description,
                    "evidence": rf.evidence,
                    "confidence": rf.confidence,
                }
                for rf in self.risk_factors
            ],
            "knowledge_owners": self.knowledge_owners,
            "recent_activity": self.recent_activity,
            "recommendations": self.recommendations,
        }


class Simulator:
    """Graph-based simulation engine.

    Implements the "what if?" query that Koratana calls
    "the test of understanding" for a context graph.
    """

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def what_if_change(self, file_path: str) -> SimulationResult:
        """Simulate: what happens if this file is changed?

        This combines all 5 coordinate systems:
        1. Timeline: recent changes to this file and neighbors
        2. Events: historical incidents involving this file
        3. Semantics: dependency relationships (blast radius)
        4. Attribution: who knows about this code
        5. Outcomes: what happened when similar changes were made
        """
        result = SimulationResult(file_path=file_path)

        # --- COORDINATE 1: Semantics (dependency blast radius) ---
        blast = self._compute_blast_radius(file_path)
        result.blast_radius = blast

        if blast["total_affected"] > 10:
            result.risk_factors.append(RiskFactor(
                category="blast_radius",
                severity="high",
                description=f"This file has {blast['total_affected']} transitive dependents. Changes ripple widely.",
                evidence=[f"Direct: {', '.join(blast['direct_dependents'][:5])}"],
                confidence=0.9,
            ))
        elif blast["total_affected"] > 3:
            result.risk_factors.append(RiskFactor(
                category="blast_radius",
                severity="medium",
                description=f"This file has {blast['total_affected']} transitive dependents.",
                evidence=[f"Direct: {', '.join(blast['direct_dependents'][:5])}"],
                confidence=0.9,
            ))

        # --- COORDINATE 2: Events (historical incidents) ---
        incidents = self._find_historical_incidents(file_path)
        result.historical_incidents = incidents

        if len(incidents) >= 3:
            result.risk_factors.append(RiskFactor(
                category="incident_history",
                severity="high",
                description=f"This file has {len(incidents)} historical incidents. It's a hotspot.",
                evidence=[inc["summary"] for inc in incidents[:3]],
                confidence=0.85,
            ))
        elif len(incidents) >= 1:
            result.risk_factors.append(RiskFactor(
                category="incident_history",
                severity="medium",
                description=f"This file has {len(incidents)} prior incident(s).",
                evidence=[inc["summary"] for inc in incidents[:3]],
                confidence=0.8,
            ))

        # --- COORDINATE 3: Outcomes (recurring patterns) ---
        patterns = self._find_recurring_patterns(file_path)
        result.recurring_patterns = patterns

        for pattern in patterns:
            if pattern["count"] >= 2:
                result.risk_factors.append(RiskFactor(
                    category="recurring_pattern",
                    severity="medium",
                    description=f"Pattern '{pattern['category']}' has recurred {pattern['count']} times in this area.",
                    evidence=[fix["summary"] for fix in pattern.get("recent_fixes", [])[:2]],
                    confidence=0.75,
                ))

        # --- COORDINATE 4: Attribution (knowledge owners) ---
        owners = self._find_knowledge_owners(file_path)
        result.knowledge_owners = owners

        if not owners:
            result.risk_factors.append(RiskFactor(
                category="knowledge_gap",
                severity="medium",
                description="No knowledge owners identified for this file. Context debt risk.",
                confidence=0.6,
            ))

        # --- COORDINATE 5: Timeline (recent activity) ---
        recent = self._find_recent_activity(file_path)
        result.recent_activity = recent

        if len(recent) >= 5:
            result.risk_factors.append(RiskFactor(
                category="churn",
                severity="medium",
                description=f"This file has been changed {len(recent)} times recently. High churn = higher risk.",
                evidence=[f"{r['date']}: {r['message']}" for r in recent[:3]],
                confidence=0.7,
            ))

        # --- Compute overall risk ---
        result.overall_risk = self._compute_overall_risk(result.risk_factors)
        result.confidence = self._compute_confidence(result.risk_factors)

        # --- Generate recommendations ---
        result.recommendations = self._generate_recommendations(result)

        # --- Build simulation context for Claude ---
        result.simulation_context = self._build_claude_context(result)

        logger.info(
            "Simulation complete",
            extra={
                "file": file_path,
                "risk": result.overall_risk,
                "factors": len(result.risk_factors),
            },
        )

        return result

    def _compute_blast_radius(self, file_path: str) -> dict:
        """Find all files that depend on this file (directly or transitively)."""
        # Find the file's node
        file_nodes = self._store.find_nodes_by_property(
            "file_path", file_path, NodeType.CODE_UNIT
        )
        if not file_nodes:
            return {"direct_dependents": [], "transitive_dependents": [], "total_affected": 0}

        file_node = file_nodes[0]

        # BFS through DEPENDS_ON edges (reversed -- find who depends on US)
        direct: list[str] = []
        transitive: list[str] = []
        visited: set[str] = {file_node.id}
        queue: list[tuple[str, int]] = [(file_node.id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            edges = self._store.get_edges_to(current_id)

            for edge in edges:
                if edge.edge_type == EdgeType.DEPENDS_ON and edge.source_id not in visited:
                    visited.add(edge.source_id)
                    dep_node = self._store.get_node(edge.source_id)
                    if dep_node:
                        dep_path = str(dep_node.properties.get("file_path", dep_node.name))
                        if depth == 0:
                            direct.append(dep_path)
                        else:
                            transitive.append(dep_path)
                        queue.append((edge.source_id, depth + 1))

        return {
            "direct_dependents": direct,
            "transitive_dependents": transitive,
            "total_affected": len(direct) + len(transitive),
        }

    def _find_historical_incidents(self, file_path: str) -> list[dict]:
        """Find all decision traces (incidents/fixes) for this file."""
        traces = self._store.get_nodes_by_type(NodeType.DECISION_TRACE)
        results: list[dict] = []

        for node in traces:
            files_str = str(node.properties.get("files_affected", ""))
            if file_path in files_str:
                results.append({
                    "id": node.id,
                    "summary": node.name,
                    "type": str(node.properties.get("decision_type", "")),
                    "rationale": str(node.properties.get("rationale", "")),
                    "categories": str(node.properties.get("categories", "")).split("|"),
                    "date": node.created_at,
                })

        results.sort(key=lambda x: x["date"], reverse=True)
        return results

    def _find_recurring_patterns(self, file_path: str) -> list[dict]:
        """Find fix patterns that recur in this file or nearby files."""
        incidents = self._find_historical_incidents(file_path)
        category_counts: dict[str, dict] = {}

        for inc in incidents:
            for cat in inc.get("categories", []):
                if not cat:
                    continue
                if cat not in category_counts:
                    category_counts[cat] = {"category": cat, "count": 0, "recent_fixes": []}
                category_counts[cat]["count"] += 1
                if len(category_counts[cat]["recent_fixes"]) < 3:
                    category_counts[cat]["recent_fixes"].append({
                        "summary": inc["summary"],
                        "rationale": inc["rationale"],
                    })

        return sorted(category_counts.values(), key=lambda p: p["count"], reverse=True)

    def _find_knowledge_owners(self, file_path: str) -> list[dict]:
        """Find who has the most context on this file (from git blame/attribution)."""
        # Look for CODE_CHANGE nodes that modified this file
        file_nodes = self._store.find_nodes_by_property(
            "file_path", file_path, NodeType.CODE_UNIT
        )
        if not file_nodes:
            return []

        author_counts: dict[str, int] = {}
        for file_node in file_nodes:
            edges = self._store.get_edges_to(file_node.id)
            for edge in edges:
                if edge.edge_type == EdgeType.MODIFIES:
                    commit_node = self._store.get_node(edge.source_id)
                    if commit_node:
                        author = str(commit_node.properties.get("author", "unknown"))
                        author_counts[author] = author_counts.get(author, 0) + 1

        owners = [
            {"author": author, "changes": count}
            for author, count in sorted(
                author_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]
        return owners[:10]

    def _find_recent_activity(self, file_path: str) -> list[dict]:
        """Find recent code changes to this file."""
        file_nodes = self._store.find_nodes_by_property(
            "file_path", file_path, NodeType.CODE_UNIT
        )
        if not file_nodes:
            return []

        changes: list[dict] = []
        for file_node in file_nodes:
            edges = self._store.get_edges_to(file_node.id)
            for edge in edges:
                if edge.edge_type == EdgeType.MODIFIES:
                    commit = self._store.get_node(edge.source_id)
                    if commit:
                        changes.append({
                            "commit": str(commit.properties.get("commit_hash", ""))[:8],
                            "author": str(commit.properties.get("author", "")),
                            "date": str(commit.properties.get("date", "")),
                            "message": commit.name,
                        })

        changes.sort(key=lambda x: x["date"], reverse=True)
        return changes[:20]

    def _compute_overall_risk(self, factors: list[RiskFactor]) -> str:
        """Compute overall risk from individual factors."""
        if not factors:
            return "low"

        high_count = sum(1 for f in factors if f.severity == "high")
        medium_count = sum(1 for f in factors if f.severity == "medium")

        if high_count >= 2:
            return "high"
        if high_count >= 1 or medium_count >= 3:
            return "high"
        if medium_count >= 1:
            return "medium"
        return "low"

    def _compute_confidence(self, factors: list[RiskFactor]) -> float:
        """Compute confidence in the risk assessment."""
        if not factors:
            return 0.0
        avg = sum(f.confidence for f in factors) / len(factors)
        return round(min(avg, 1.0), 2)

    def _generate_recommendations(self, result: SimulationResult) -> list[str]:
        """Generate actionable recommendations based on simulation."""
        recs: list[str] = []

        if result.overall_risk == "high":
            recs.append("HIGH RISK: Request thorough code review before merging.")

        for factor in result.risk_factors:
            if factor.category == "blast_radius" and factor.severity == "high":
                recs.append(
                    f"Run tests for all {result.blast_radius['total_affected']} affected files."
                )
            elif factor.category == "incident_history":
                recs.append(
                    "Review historical incidents for this file before making changes."
                )
            elif factor.category == "recurring_pattern":
                recs.append(
                    f"Watch for recurring pattern: {factor.description}"
                )
            elif factor.category == "knowledge_gap":
                recs.append(
                    "No knowledge owner found. Document your changes thoroughly."
                )
            elif factor.category == "churn":
                recs.append(
                    "High churn file. Coordinate with recent authors to avoid conflicts."
                )

        if result.knowledge_owners:
            top = result.knowledge_owners[0]
            recs.append(
                f"Consult {top['author']} ({top['changes']} changes) for context."
            )

        return recs

    def _build_claude_context(self, result: SimulationResult) -> str:
        """Build a markdown context block for feeding to Claude for deeper simulation.

        This is how we bridge the gap to Sim-1: give Claude the graph context
        and let it do the behavioral simulation.
        """
        lines: list[str] = []
        lines.append(f"# Simulation Context: {result.file_path}")
        lines.append(f"\n## Risk Assessment: {result.overall_risk.upper()} (confidence: {result.confidence})")

        if result.blast_radius.get("direct_dependents"):
            lines.append("\n## Blast Radius")
            lines.append(f"Direct dependents ({len(result.blast_radius['direct_dependents'])}):")
            for dep in result.blast_radius["direct_dependents"][:10]:
                lines.append(f"  - {dep}")
            if result.blast_radius.get("transitive_dependents"):
                lines.append(f"Transitive dependents ({len(result.blast_radius['transitive_dependents'])}):")
                for dep in result.blast_radius["transitive_dependents"][:10]:
                    lines.append(f"  - {dep}")

        if result.historical_incidents:
            lines.append("\n## Historical Incidents (what broke before)")
            for inc in result.historical_incidents[:5]:
                lines.append(f"  - [{inc['date'][:10]}] {inc['summary']}")
                lines.append(f"    Rationale: {inc['rationale']}")
                lines.append(f"    Categories: {', '.join(inc['categories'])}")

        if result.recurring_patterns:
            lines.append("\n## Recurring Patterns")
            for pat in result.recurring_patterns:
                lines.append(f"  - {pat['category']} ({pat['count']}x)")

        if result.knowledge_owners:
            lines.append("\n## Knowledge Owners")
            for owner in result.knowledge_owners[:5]:
                lines.append(f"  - {owner['author']} ({owner['changes']} changes)")

        if result.recent_activity:
            lines.append("\n## Recent Activity")
            for act in result.recent_activity[:5]:
                lines.append(f"  - [{act['date'][:10]}] {act['message']} ({act['author']})")

        lines.append("\n## Recommendations")
        for rec in result.recommendations:
            lines.append(f"  - {rec}")

        lines.append("\n---")
        lines.append("Use this context to simulate the behavioral impact of changes to this file.")
        lines.append("Step through the code paths that depend on this file and predict:")
        lines.append("1. What state changes could break?")
        lines.append("2. Which edge cases are most likely to fail?")
        lines.append("3. What tests should be added?")

        return "\n".join(lines)
