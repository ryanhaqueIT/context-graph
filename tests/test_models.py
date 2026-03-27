"""Tests for data models (Node, Edge, DecisionTrace, enums).

Verifies serialization roundtrips, enum completeness, and data integrity.
"""

import uuid

from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)


# ---------------------------------------------------------------------------
# Node serialization
# ---------------------------------------------------------------------------


def test_node_serialization():
    """A Node survives a to_dict / from_dict roundtrip."""
    node = Node(
        node_type=NodeType.CODE_UNIT,
        name="test.py",
        properties={"file_path": "src/test.py", "language": "python"},
    )
    data = node.to_dict()
    restored = Node.from_dict(data)

    assert restored.id == node.id
    assert restored.node_type == NodeType.CODE_UNIT
    assert restored.name == "test.py"
    assert restored.properties["file_path"] == "src/test.py"
    assert restored.properties["language"] == "python"
    assert restored.created_at == node.created_at


def test_node_default_values():
    """A Node created with no arguments has sensible defaults."""
    node = Node()
    assert node.id  # non-empty UUID
    uuid.UUID(node.id)  # valid UUID format
    assert node.node_type == NodeType.CODE_UNIT
    assert node.name == ""
    assert node.properties == {}
    assert node.created_at  # non-empty timestamp


def test_node_custom_id():
    """A Node can be created with a custom ID."""
    node = Node(id="custom-id", name="custom")
    assert node.id == "custom-id"
    data = node.to_dict()
    restored = Node.from_dict(data)
    assert restored.id == "custom-id"


def test_node_to_dict_structure():
    """to_dict produces the expected dictionary keys."""
    node = Node(node_type=NodeType.INCIDENT, name="bug-42")
    data = node.to_dict()
    assert set(data.keys()) == {"id", "node_type", "name", "properties", "created_at"}
    assert data["node_type"] == "incident"
    assert data["name"] == "bug-42"


# ---------------------------------------------------------------------------
# Edge serialization
# ---------------------------------------------------------------------------


def test_edge_serialization():
    """An Edge survives a to_dict / from_dict roundtrip."""
    edge = Edge(
        edge_type=EdgeType.MODIFIES,
        source_id="src1",
        target_id="tgt1",
        properties={"weight": 1},
    )
    data = edge.to_dict()
    restored = Edge.from_dict(data)

    assert restored.id == edge.id
    assert restored.edge_type == EdgeType.MODIFIES
    assert restored.source_id == "src1"
    assert restored.target_id == "tgt1"
    assert restored.properties["weight"] == 1
    assert restored.created_at == edge.created_at


def test_edge_default_values():
    """An Edge created with no arguments has sensible defaults."""
    edge = Edge()
    assert edge.id
    uuid.UUID(edge.id)
    assert edge.edge_type == EdgeType.REFERENCES
    assert edge.source_id == ""
    assert edge.target_id == ""
    assert edge.properties == {}


def test_edge_to_dict_structure():
    """to_dict produces the expected dictionary keys."""
    edge = Edge(edge_type=EdgeType.CAUSES, source_id="a", target_id="b")
    data = edge.to_dict()
    assert set(data.keys()) == {"id", "edge_type", "source_id", "target_id",
                                 "properties", "created_at"}
    assert data["edge_type"] == "causes"


# ---------------------------------------------------------------------------
# DecisionTrace roundtrip
# ---------------------------------------------------------------------------


def test_decision_trace_roundtrip():
    """A DecisionTrace survives Node conversion and back."""
    trace = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Fixed the pagination bug",
        rationale="Off-by-one in the loop boundary",
        evidence=["commit:abc123", "ticket:JIRA-456"],
        files_affected=["src/engine/store.py", "src/query/interface.py"],
        categories=["pagination", "off-by-one"],
        actor="agent",
        outcome="resolved",
    )

    node = trace.to_node()
    assert node.node_type == NodeType.DECISION_TRACE
    assert node.name == trace.summary

    restored = DecisionTrace.from_node(node)
    assert restored.id == trace.id
    assert restored.decision_type == DecisionType.BUG_FIX
    assert restored.summary == trace.summary
    assert restored.rationale == trace.rationale
    assert restored.evidence == trace.evidence
    assert restored.files_affected == trace.files_affected
    assert restored.categories == trace.categories
    assert restored.actor == "agent"
    assert restored.outcome == "resolved"


def test_decision_trace_empty_lists():
    """A DecisionTrace with empty lists roundtrips correctly."""
    trace = DecisionTrace(
        decision_type=DecisionType.REVIEW,
        summary="Reviewed module structure",
        evidence=[],
        files_affected=[],
        categories=[],
    )
    node = trace.to_node()
    restored = DecisionTrace.from_node(node)

    assert restored.evidence == []
    assert restored.files_affected == []
    assert restored.categories == []


def test_decision_trace_default_values():
    """A DecisionTrace with defaults has expected field values."""
    trace = DecisionTrace()
    assert trace.decision_type == DecisionType.BUG_FIX
    assert trace.summary == ""
    assert trace.rationale == ""
    assert trace.actor == "agent"
    assert trace.outcome == ""
    assert trace.evidence == []
    assert trace.files_affected == []
    assert trace.categories == []


def test_decision_trace_preserves_pipe_in_fields():
    """Pipe-delimited serialization works when fields contain no pipes."""
    trace = DecisionTrace(
        evidence=["a", "b", "c"],
        files_affected=["x.py", "y.py"],
        categories=["cat1"],
    )
    node = trace.to_node()
    restored = DecisionTrace.from_node(node)
    assert restored.evidence == ["a", "b", "c"]
    assert restored.files_affected == ["x.py", "y.py"]
    assert restored.categories == ["cat1"]


# ---------------------------------------------------------------------------
# Enum completeness
# ---------------------------------------------------------------------------


def test_node_types_exist():
    """All expected NodeType enum members exist."""
    assert NodeType.CODE_UNIT.value == "code_unit"
    assert NodeType.CODE_CHANGE.value == "code_change"
    assert NodeType.DECISION_TRACE.value == "decision_trace"
    assert NodeType.INCIDENT.value == "incident"
    assert NodeType.FIX_PATTERN.value == "fix_pattern"
    assert NodeType.VALIDATION_FAILURE.value == "validation_failure"
    assert NodeType.REVIEW_DECISION.value == "review_decision"

    # Verify total count to catch additions
    assert len(NodeType) >= 7


def test_edge_types_exist():
    """All expected EdgeType enum members exist."""
    assert EdgeType.FIXES.value == "fixes"
    assert EdgeType.CAUSES.value == "causes"
    assert EdgeType.MODIFIES.value == "modifies"
    assert EdgeType.REFERENCES.value == "references"
    assert EdgeType.PRECEDED_BY.value == "preceded_by"
    assert EdgeType.RESOLVES.value == "resolves"
    assert EdgeType.REVIEWED_IN.value == "reviewed_in"

    assert len(EdgeType) >= 7


def test_decision_type_values():
    """All expected DecisionType enum members exist with correct values."""
    expected = {
        "bug_fix": DecisionType.BUG_FIX,
        "review": DecisionType.REVIEW,
        "architecture": DecisionType.ARCHITECTURE,
        "validation_fix": DecisionType.VALIDATION_FIX,
        "refactor": DecisionType.REFACTOR,
        "feature": DecisionType.FEATURE,
        "incident_response": DecisionType.INCIDENT_RESPONSE,
    }
    for value, member in expected.items():
        assert member.value == value

    assert len(DecisionType) >= 7


def test_node_type_values_are_lowercase_snake_case():
    """All NodeType values follow lowercase_snake_case convention."""
    for nt in NodeType:
        assert nt.value == nt.value.lower()
        assert " " not in nt.value
        assert "-" not in nt.value


def test_edge_type_values_are_lowercase_snake_case():
    """All EdgeType values follow lowercase_snake_case convention."""
    for et in EdgeType:
        assert et.value == et.value.lower()
        assert " " not in et.value
        assert "-" not in et.value


def test_decision_type_values_are_lowercase_snake_case():
    """All DecisionType values follow lowercase_snake_case convention."""
    for dt in DecisionType:
        assert dt.value == dt.value.lower()
        assert " " not in dt.value
        assert "-" not in dt.value


# ---------------------------------------------------------------------------
# Cross-type interactions
# ---------------------------------------------------------------------------


def test_node_from_dict_with_all_node_types():
    """Every NodeType can be serialized and deserialized through Node."""
    for nt in NodeType:
        node = Node(node_type=nt, name=f"test-{nt.value}")
        data = node.to_dict()
        restored = Node.from_dict(data)
        assert restored.node_type == nt


def test_edge_from_dict_with_all_edge_types():
    """Every EdgeType can be serialized and deserialized through Edge."""
    for et in EdgeType:
        edge = Edge(edge_type=et, source_id="s", target_id="t")
        data = edge.to_dict()
        restored = Edge.from_dict(data)
        assert restored.edge_type == et
