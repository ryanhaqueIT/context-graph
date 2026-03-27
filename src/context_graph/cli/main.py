"""CLI entry point: init, scan, ingest, record, query, health, trajectory."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from context_graph.config.settings import get_graph_dir, get_log_level, get_repo_root
from context_graph.engine.store import GraphStore
from context_graph.ingest.git_ingest import ingest_git_history
# multi_lang_parser is imported lazily inside cmd_scan() to avoid hard dependency at import time
from context_graph.models.nodes import DecisionTrace, DecisionType, Edge, EdgeType, Node, NodeType
from context_graph.query.interface import QueryInterface

logging.basicConfig(level=get_log_level(), format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DECISION_TYPE_MAP: dict[str, DecisionType] = {
    "fix": DecisionType.BUG_FIX,
    "review": DecisionType.REVIEW,
    "architecture": DecisionType.ARCHITECTURE,
    "validation": DecisionType.VALIDATION_FIX,
    "refactor": DecisionType.REFACTOR,
    "feature": DecisionType.FEATURE,
    "incident": DecisionType.INCIDENT_RESPONSE,
}


def _load_store(args: argparse.Namespace) -> GraphStore | None:
    """Load and initialize the store, returning None if uninitialized."""
    store = GraphStore(get_graph_dir(getattr(args, "dir", None)))
    if not store.is_initialized:
        print("Error: graph not initialized. Run 'context-graph init' first.", file=sys.stderr)
        return None
    store.initialize()
    return store


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize the context graph store."""
    graph_dir = get_graph_dir(getattr(args, "dir", None))
    GraphStore(graph_dir).initialize()
    print(f"Context graph initialized at {graph_dir}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan codebase for code understanding using multi-language tree-sitter parsing."""
    from context_graph.ingest.multi_lang_parser import MultiLanguageParser, SymbolResolver

    store = _load_store(args)
    if not store:
        return 1

    repo_root = get_repo_root()
    parser = MultiLanguageParser()
    results = parser.parse_directory(repo_root, repo_root=repo_root)

    # Collect all symbols and references across files.
    all_symbols = []
    all_references = []
    lang_counts: dict[str, int] = {}
    node_count = 0

    for result in results:
        all_symbols.extend(result.symbols)
        all_references.extend(result.references)
        lang_counts[result.language] = lang_counts.get(result.language, 0) + 1

        # Create CODE_UNIT nodes for each symbol.
        for sym in result.symbols:
            node_name = sym.qualified_name
            existing = store.find_nodes_by_property("file_path", sym.file_path, NodeType.CODE_UNIT)
            already = any(
                n.name == node_name and n.properties.get("start_line") == sym.start_line
                for n in existing
            )
            if already:
                continue
            store.add_node(
                Node(
                    node_type=NodeType.CODE_UNIT,
                    name=node_name,
                    properties={
                        "file_path": sym.file_path,
                        "language": sym.language,
                        "kind": sym.kind,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                        "parent": sym.parent or "",
                    },
                )
            )
            node_count += 1

    # Resolve references and create DEPENDS_ON edges.
    resolver = SymbolResolver(all_symbols)
    edge_count = 0
    for ref, target_sym in resolver.resolve_all(all_references):
        if target_sym is None:
            continue
        # Find source and target nodes.
        src_nodes = [
            n
            for n in store.find_nodes_by_property("file_path", ref.file_path, NodeType.CODE_UNIT)
            if n.name == ref.source_symbol
        ]
        tgt_nodes = [
            n
            for n in store.find_nodes_by_property(
                "file_path", target_sym.file_path, NodeType.CODE_UNIT
            )
            if n.name == target_sym.qualified_name
        ]
        if not src_nodes or not tgt_nodes:
            continue
        src_node, tgt_node = src_nodes[0], tgt_nodes[0]
        if src_node.id == tgt_node.id:
            continue
        # Skip duplicates.
        existing_edges = store.get_edges_from(src_node.id)
        if any(
            e.target_id == tgt_node.id and e.edge_type == EdgeType.DEPENDS_ON
            for e in existing_edges
        ):
            continue
        store.add_edge(
            Edge(
                edge_type=EdgeType.DEPENDS_ON,
                source_id=src_node.id,
                target_id=tgt_node.id,
                properties={"relationship": ref.kind},
            )
        )
        edge_count += 1

    # Report.
    lang_report = ", ".join(f"{lang}: {cnt}" for lang, cnt in sorted(lang_counts.items()))
    print(f"Scanned {len(results)} files ({lang_report}).")
    print(f"  Symbols: {node_count} new nodes. Edges: {edge_count} new DEPENDS_ON edges.")
    print(f"  Graph total: {store.node_count} nodes, {store.edge_count} edges.")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest data sources into the context graph."""
    store = _load_store(args)
    if not store:
        return 1
    if args.source != "git":
        print(f"Unknown source: {args.source}", file=sys.stderr)
        return 1
    count = ingest_git_history(store, max_commits=args.limit or 500)
    print(f"Ingested {count} commits. Graph: {store.node_count} nodes, {store.edge_count} edges.")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    """Record a DecisionTrace."""
    store = _load_store(args)
    if not store:
        return 1
    files = args.file if isinstance(args.file, list) else [args.file] if args.file else []
    trace = DecisionTrace(
        decision_type=DECISION_TYPE_MAP.get(args.type, DecisionType.BUG_FIX),
        summary=args.summary or f"{args.type} on {', '.join(files)}",
        rationale=args.rationale or "",
        evidence=args.evidence.split(",") if args.evidence else [],
        files_affected=files,
        categories=args.category.split(",") if args.category else [],
        actor=args.actor or "agent",
        outcome=args.outcome or "resolved",
    )
    store.add_node(trace.to_node())
    print(f"DecisionTrace recorded: {trace.id}")
    print(f"  Type: {trace.decision_type.value}  Files: {', '.join(trace.files_affected)}")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Route to the appropriate query handler."""
    store = _load_store(args)
    if not store:
        return 1
    qi = QueryInterface(store)
    dispatch: dict = {
        "incidents": _q_incidents,
        "decisions": _q_decisions,
        "patterns": _q_patterns,
        "changes": _q_changes,
        "blast-radius": _q_blast,
        "owners": _q_owners,
        "what-if": _q_whatif,
    }
    handler = dispatch.get(args.query_type)
    return handler(args, qi) if handler else 1


def _q_incidents(a: argparse.Namespace, qi: QueryInterface) -> int:
    if not a.file:
        print("Error: --file required", file=sys.stderr)
        return 1
    traces = qi.incidents_for_file(a.file)
    if not traces:
        print(f"No incidents found for {a.file}")
        return 0
    print(f"Found {len(traces)} incident(s) for {a.file}:\n")
    for t in traces:
        print(f"  [{t.created_at[:10]}] {t.summary} | {t.rationale}")
    return 0


def _q_decisions(a: argparse.Namespace, qi: QueryInterface) -> int:
    if not a.module:
        print("Error: --module required", file=sys.stderr)
        return 1
    traces = qi.decisions_for_module(a.module)
    if not traces:
        print(f"No decisions found for module {a.module}")
        return 0
    print(f"Found {len(traces)} decision(s) for {a.module}:\n")
    for t in traces:
        print(f"  [{t.created_at[:10]}] {t.summary} | {t.rationale}")
    return 0


def _q_patterns(a: argparse.Namespace, qi: QueryInterface) -> int:
    for p in qi.fix_patterns(category=a.category):
        print(f"  [{p['category']}] ({p['count']}x)")
        for fix in p["recent_fixes"]:
            print(f"    - {fix['summary']}")
    return 0


def _q_changes(a: argparse.Namespace, qi: QueryInterface) -> int:
    for c in qi.recent_changes(file_path=a.file, limit=a.limit or 20):
        h = str(c.properties.get("commit_hash", ""))[:8]
        print(f"  [{str(c.properties.get('date', ''))[:10]}] {c.name} ({h})")
    return 0


def _q_blast(a: argparse.Namespace, qi: QueryInterface) -> int:
    if not a.file:
        print("Error: --file required", file=sys.stderr)
        return 1
    print(json.dumps(qi.blast_radius(a.file), indent=2))
    return 0


def _q_owners(a: argparse.Namespace, qi: QueryInterface) -> int:
    if not a.file:
        print("Error: --file required", file=sys.stderr)
        return 1
    for o in qi.knowledge_owners(a.file):
        commits, traces, score = o["commits"], o["traces"], o["score"]
        print(f"  {o['author']}: {commits} commits, {traces} traces (score: {score})")
    return 0


def _q_whatif(a: argparse.Namespace, qi: QueryInterface) -> int:
    if not a.file:
        print("Error: --file required", file=sys.stderr)
        return 1
    print(json.dumps(qi.what_if_change(a.file), indent=2))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Show context graph health report."""
    store = _load_store(args)
    if not store:
        return 1
    r = QueryInterface(store).health_report()
    print("Context Graph Health Report\n" + "=" * 50)
    hkeys = "total_nodes total_edges code_units decision_traces"
    hkeys += " code_changes files_with_traces files_without_traces"
    for key in hkeys.split():
        print(f"  {key.replace('_', ' ').title():20s} {r[key]}")
    print(f"  {'Coverage Ratio':20s} {r['coverage_ratio']:.1%}")
    for f in r.get("uncovered_files", [])[:10]:
        print(f"    - {f}")
    return 0


def cmd_trajectory(args: argparse.Namespace) -> int:
    """Manage agent trajectory recordings."""
    store = _load_store(args)
    if not store:
        return 1
    if args.action == "start":
        tid = store.start_trajectory(
            agent_id=args.actor if hasattr(args, "actor") and args.actor else "agent",
            description=args.description or "",
        )
        print(f"Trajectory started: {tid}")
    elif args.action == "step":
        if not args.id or not args.node:
            print("Error: --id and --node required", file=sys.stderr)
            return 1
        action = args.description or "step"
        store.record_step(trajectory_id=args.id, node_id=args.node, action=action)
        print(f"Trajectory step recorded for {args.id[:8]}")
    elif args.action == "end":
        if not args.id:
            print("Error: --id required", file=sys.stderr)
            return 1
        traj = store.get_trajectory(args.id)
        if not traj:
            print(f"Trajectory {args.id} not found", file=sys.stderr)
            return 1
        store.end_trajectory(args.id)
        print(f"Trajectory ended: {args.id}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the FastAPI API server."""
    import uvicorn

    host = getattr(args, "host", "0.0.0.0") or "0.0.0.0"
    port = getattr(args, "port", 8000) or 8000

    # If --dir is specified, set it in the environment so the API dep picks it up
    graph_dir = getattr(args, "dir", None)
    if graph_dir:
        import os
        os.environ["CONTEXT_GRAPH_DIR"] = graph_dir

    print(f"Starting Context Graph API server on {host}:{port}")
    uvicorn.run("context_graph.api.server:app", host=host, port=port, reload=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(prog="context-graph", description="Context graph engine")
    p.add_argument("--dir", help="Graph store directory override")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize the context graph store")
    sub.add_parser("scan", help="Scan codebase for code understanding")
    ig = sub.add_parser("ingest", help="Ingest data sources")
    ig.add_argument("source", choices=["git"], help="Data source")
    ig.add_argument("--limit", type=int, default=500, help="Max items")
    rc = sub.add_parser("record", help="Record a DecisionTrace")
    rc.add_argument("--type", required=True, choices=list(DECISION_TYPE_MAP.keys()))
    rc.add_argument("--file", action="append", help="File(s) affected")
    rc.add_argument("--summary", help="Summary")
    rc.add_argument("--rationale", help="Why this decision was made")
    rc.add_argument("--evidence", help="Comma-separated evidence")
    rc.add_argument("--category", help="Comma-separated categories")
    rc.add_argument("--actor", default="agent", help="Actor")
    rc.add_argument("--outcome", default="resolved", help="Outcome")
    qp = sub.add_parser("query", help="Query the context graph")
    qt = "incidents decisions patterns changes blast-radius owners what-if"
    qp.add_argument("query_type", choices=qt.split())
    qp.add_argument("--file", help="File path")
    qp.add_argument("--module", help="Module/directory")
    qp.add_argument("--category", help="Category filter")
    qp.add_argument("--limit", type=int, help="Max results")
    sub.add_parser("health", help="Show graph health report")
    tp = sub.add_parser("trajectory", help="Manage agent trajectories")
    tp.add_argument("action", choices=["start", "step", "end"])
    tp.add_argument("--description", help="Trajectory description")
    tp.add_argument("--id", help="Trajectory ID")
    tp.add_argument("--node", help="Node ID for trajectory step")
    sp = sub.add_parser("serve", help="Start the API server")
    sp.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    sp.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    return p


def main() -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    cmds: dict = {
        "init": cmd_init,
        "scan": cmd_scan,
        "ingest": cmd_ingest,
        "record": cmd_record,
        "query": cmd_query,
        "health": cmd_health,
        "trajectory": cmd_trajectory,
        "serve": cmd_serve,
    }
    handler = cmds.get(args.command)
    sys.exit(handler(args) if handler else (parser.print_help() or 1))


if __name__ == "__main__":
    main()
