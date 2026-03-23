# Context Graph x Harness Engineering: Integration Analysis

## The Gap in the Current Harness

Your harness engineering framework is a **map** -- it tells agents:
- WHERE things are (ARCHITECTURE.md)
- WHAT to do and not do (three-tier boundaries)
- HOW to verify (22 validation gates, ratchet, scorecard)

What it lacks is **memory** -- it doesn't tell agents:
- WHY things are built the way they are
- WHAT broke before and how it was fixed
- WHAT decisions led to the current architecture
- WHAT patterns recur when things go wrong

**PlayerZero's context graph is exactly this memory layer.**

---

## Mapping: PlayerZero Concepts -> Harness Primitives

| PlayerZero Concept | Harness Equivalent | Gap |
|---|---|---|
| Context Graph | No equivalent | **The core missing piece** |
| DecisionTrace | ADRs (docs/adr/) | ADRs are static docs. DecisionTraces are queryable, linked graph nodes with evidence |
| Production World Model | ARCHITECTURE.md + repo profile | Architecture is a snapshot. World model is live + predictive |
| CodeSim / Sim-1 | validate.sh + lint gates | Gates verify syntax/style. Sim predicts behavioral correctness |
| Scenarios | Feature list (.harness/feature_list.json) | Feature list tracks pass/fail. Scenarios encode expected behavior in plain English |
| Playbooks (investigation patterns) | Slash commands (validate, review, etc.) | Commands are imperative actions. Playbooks are evidence-backed reasoning patterns |
| Fix patterns | No equivalent | Each bug is solved from scratch today |
| RL graph traversal | No equivalent | Agents can't navigate accumulated knowledge |
| MCP Server (retrieval) | No equivalent | Agents can't query institutional memory |

---

## What a Context Graph Gives Every Harness Agent

### Today: Agent encounters a bug
```
1. Agent reads ARCHITECTURE.md (what exists)
2. Agent reads AGENTS.md (what rules to follow)
3. Agent reads the code (what it does)
4. Agent guesses at root cause
5. Agent proposes fix based on general knowledge
6. validate.sh checks syntax/style
7. Reviewer agent scores against rubric
```

### With Context Graph: Agent encounters a bug
```
1. Agent queries context graph: "What broke near this code before?"
2. Graph returns: 3 prior incidents in this module
   - Incident #12: off-by-one in pagination (fixed by commit abc123)
   - Incident #27: race condition in cache invalidation (took 3 days)
   - Incident #31: null pointer when external API times out (pattern: always add timeout)
3. Agent queries: "What DecisionTraces exist for this service?"
4. Graph returns: "Service was split from monolith in Q2 2025.
   Rationale: billing team needed independent deploys.
   Known constraint: shared DB means state can drift."
5. Agent proposes fix WITH historical context
6. CodeSim simulates fix against production world model
7. Fix verified against known failure patterns, not just lint rules
```

---

## Integration Architecture

### Layer 1: Graph Engine (Foundation)
Embed an in-process graph database into the harness infrastructure.

**Option A (Lightweight)**: JSONL-based graph with file storage
- Nodes and edges stored as JSON files in `.harness/context-graph/`
- Simple but limited -- works for small codebases
- No query language, just grep/jq

**Option B (Production)**: KuzuDB embedded (what PlayerZero uses)
- In-process, embedded graph database
- Cypher query language
- Python bindings (fits your script ecosystem)
- pip install kuzu

**Option C (Scaled)**: Neo4j or similar managed service
- Full graph database with visualization
- Better for CBA-scale (7,800 engineers)
- Requires infrastructure

### Layer 2: Data Ingestion Hooks
Wire context graph capture into existing harness touchpoints:

| Harness Event | Context Graph Action |
|---|---|
| `validate.sh` failure | Create `ValidationFailure` node, link to changed files |
| `validate.sh` passes after failure | Create `DecisionTrace`: what failed, what fixed it |
| Code review (reviewer.md) | Create `ReviewDecision` node with scores + feedback |
| Ratchet improvement | Create `QualityImprovement` node, track trajectory |
| Feature list change | Create `FeatureDecision` node, capture intent |
| Bootstrap discovery | Create `ArchitecturalSnapshot` node |
| ADR creation | Create `ArchitecturalDecision` node, link to code |
| Git commit | Create `CodeChange` node, link to files, author, ticket |
| Bug fix | Create `FixPattern` node, extract minimal change pattern |
| Morning check | Create `HealthCheck` node, capture system state |

### Layer 3: Agent Query Interface
Give every harness agent the ability to query the graph:

```python
# New script: scripts/query_context.py
from context_graph import ContextGraph

graph = ContextGraph(".harness/context-graph")

# "What broke near this code before?"
graph.query_related_incidents("src/billing/invoice.py")

# "What decisions were made about this module?"
graph.query_decision_traces("src/billing/")

# "What fix patterns exist for timeout errors?"
graph.query_fix_patterns(category="timeout")

# "Who has the most context on this service?"
graph.query_knowledge_owners("billing-service")

# "What changed in the last deploy that could cause this?"
graph.query_recent_changes(since="last-deploy")
```

### Layer 4: New Harness Agents
| Agent | Role |
|---|---|
| **context-recorder** | Automatically captures DecisionTraces from agent actions |
| **incident-investigator** | Queries graph for precedent before proposing fixes |
| **pattern-extractor** | Identifies recurring fix patterns and codifies them |
| **knowledge-auditor** | Identifies context gaps (code with no DecisionTraces) |

### Layer 5: New Validation Gates
| Gate # | Name | What It Checks |
|---|---|---|
| 23 | `check_context_trace.py` | Every bug fix must have a linked DecisionTrace |
| 24 | `check_knowledge_coverage.py` | Critical modules must have decision history |
| 25 | `check_pattern_consistency.py` | Similar bugs should be fixed consistently |

---

## New Harness Bootstrap Phase: Context Graph Init

Add to the 4-phase bootstrap:

### Phase 4: Context Graph Initialization
```
Phase 0: Discover  --> repo profile
Phase 1: Analyze   --> architecture + boundaries
Phase 2: Generate  --> harness artifacts
Phase 3: Verify    --> everything works
Phase 4: Context   --> initialize context graph (NEW)
```

**Phase 4 Steps:**
1. Initialize graph store in `.harness/context-graph/`
2. Ingest git history as `CodeChange` nodes
3. Parse existing ADRs as `ArchitecturalDecision` nodes
4. Extract commit messages for `DecisionTrace` seeds
5. Map module ownership from git blame
6. Create baseline `ArchitecturalSnapshot`
7. Generate `scripts/query_context.py` and `scripts/record_trace.py`
8. Add context graph health check to `validate.sh`
9. Add new gates (23-25) to scorecard

---

## The Compound Effect for CBA

At CBA scale (7,800 engineers), context debt is massive:
- Engineers leave, knowledge walks out the door
- Teams duplicate investigations across squads
- The same bugs get fixed 10 different ways
- Nobody knows WHY the auth middleware is structured that way

With a context graph embedded in every harness:

**Month 1**: Graph seeds from git history. Basic "what changed" queries.
**Month 3**: DecisionTraces accumulate from agent actions. "Why was this fixed this way?"
**Month 6**: Fix patterns emerge. Agents auto-suggest proven solutions.
**Month 12**: Production world model forms. Agents predict "will this PR break production?"

This is the transition from **reactive debugging** to **predictive engineering**.

---

## What You Can Build Without PlayerZero

PlayerZero's full stack (Sim-1, RL traversal, CodeSim) requires years of ML engineering. But the **context graph as institutional memory** is buildable:

### Immediately buildable:
- Graph storage (KuzuDB or JSONL)
- DecisionTrace capture (hooks on harness events)
- Agent query interface (Python scripts)
- Fix pattern extraction (commit analysis)
- Knowledge coverage tracking

### Requires ML investment:
- RL-based graph traversal optimization
- Code simulation without execution (Sim-1)
- Predictive regression detection
- Automatic scenario generation

### Could integrate PlayerZero for:
- Code simulation / CodeSim
- Production world model
- Advanced RL traversal
- Session replay correlation

---

## Recommendation

**Start with the DecisionTrace primitive.**

It's the atomic unit that makes everything else work. Every time a harness agent:
- Fixes a bug -> record WHY (not just WHAT)
- Reviews code -> record the JUDGMENT (not just the score)
- Hits a validation failure -> record the RESOLUTION PATH

Wire this into a graph. Make it queryable. Give every agent access.

The context graph doesn't replace your harness -- it gives your harness a memory that compounds over time, turning 7,800 engineers' accumulated knowledge into a queryable, agent-accessible institutional brain.
