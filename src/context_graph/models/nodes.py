"""Node and edge data models for the context graph.

These are the atomic data structures stored in the graph.
Models are leaf-layer -- they import nothing from other internal modules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class NodeType(Enum):
    """Types of nodes in the context graph."""

    CODE_UNIT = "code_unit"  # File, function, module
    CODE_CHANGE = "code_change"  # Git commit
    DECISION_TRACE = "decision_trace"  # WHY something was done
    INCIDENT = "incident"  # Bug, error, issue
    FIX_PATTERN = "fix_pattern"  # Reusable fix template
    VALIDATION_FAILURE = "validation_failure"  # Harness gate failure
    REVIEW_DECISION = "review_decision"  # Code review outcome
    TRAJECTORY = "trajectory"  # Agent trajectory recording
    TRAJECTORY_STEP = "trajectory_step"  # Single step in a trajectory


class EdgeType(Enum):
    """Types of edges in the context graph."""

    FIXES = "fixes"  # This change fixes this incident
    CAUSES = "causes"  # This change caused this incident
    MODIFIES = "modifies"  # This commit modifies this file
    REFERENCES = "references"  # This trace references this evidence
    PRECEDED_BY = "preceded_by"  # Temporal ordering
    RESOLVES = "resolves"  # This pattern resolves this category
    REVIEWED_IN = "reviewed_in"  # This file was reviewed in this decision
    DEPENDS_ON = "depends_on"  # Code dependency (import/call)
    OWNED_BY = "owned_by"  # Attribution: who owns this code


class DecisionType(Enum):
    """Categories of decisions captured as DecisionTraces."""

    BUG_FIX = "bug_fix"
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    VALIDATION_FIX = "validation_fix"
    REFACTOR = "refactor"
    FEATURE = "feature"
    INCIDENT_RESPONSE = "incident_response"


@dataclass
class Node:
    """A node in the context graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.CODE_UNIT
    name: str = ""
    properties: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "properties": self.properties,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Node:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            node_type=NodeType(data["node_type"]),
            name=data["name"],
            properties=data.get("properties", {}),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Edge:
    """An edge connecting two nodes in the context graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    edge_type: EdgeType = EdgeType.REFERENCES
    source_id: str = ""
    target_id: str = ""
    properties: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "edge_type": self.edge_type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": self.properties,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Edge:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            edge_type=EdgeType(data["edge_type"]),
            source_id=data["source_id"],
            target_id=data["target_id"],
            properties=data.get("properties", {}),
            created_at=data.get("created_at", ""),
        )


@dataclass
class DecisionTrace:
    """The atomic unit of institutional knowledge.

    Captures WHY something was done, with pointers to evidence.
    This is the most important data structure in the entire system.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType = DecisionType.BUG_FIX
    summary: str = ""
    rationale: str = ""
    evidence: list[str] = field(default_factory=list)
    files_affected: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    actor: str = "agent"
    outcome: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_node(self) -> Node:
        """Convert to a graph Node for storage."""
        return Node(
            id=self.id,
            node_type=NodeType.DECISION_TRACE,
            name=self.summary,
            properties={
                "decision_type": self.decision_type.value,
                "rationale": self.rationale,
                "evidence": "|".join(self.evidence),
                "files_affected": "|".join(self.files_affected),
                "categories": "|".join(self.categories),
                "actor": self.actor,
                "outcome": self.outcome,
            },
            created_at=self.created_at,
        )

    @classmethod
    def from_node(cls, node: Node) -> DecisionTrace:
        """Reconstruct from a graph Node."""
        props = node.properties
        evidence_str = str(props.get("evidence", ""))
        files_str = str(props.get("files_affected", ""))
        categories_str = str(props.get("categories", ""))
        return cls(
            id=node.id,
            decision_type=DecisionType(str(props.get("decision_type", "bug_fix"))),
            summary=node.name,
            rationale=str(props.get("rationale", "")),
            evidence=evidence_str.split("|") if evidence_str else [],
            files_affected=files_str.split("|") if files_str else [],
            categories=categories_str.split("|") if categories_str else [],
            actor=str(props.get("actor", "agent")),
            outcome=str(props.get("outcome", "")),
            created_at=node.created_at,
        )
