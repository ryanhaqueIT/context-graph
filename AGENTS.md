# Context Graph

## THE RULE

**`./scripts/validate.sh` must exit 0 before every commit. No exceptions.**

Applies to all agents, subagents, humans, hotfixes, and "quick changes."
validate.sh auto-detects backend, frontend, and infrastructure. If it misses
something, fix validate.sh -- not this file.

## Commands

```bash
./scripts/validate.sh              # Gate -- run before every commit
./scripts/boot_worktree.sh         # Boot locally (dynamic ports)
./scripts/boot_worktree.sh --stop  # Stop local instances
./scripts/boot_worktree.sh --check # Health check running instances

cd src/context_graph && ruff check .    # Lint
cd src/context_graph && ruff format .   # Format
python -m pytest tests/                 # Test
pyright                                 # Type check
```

## Module Dependency Rules

```
cli/    -> engine/, query/, ingest/, config/, models/
query/  -> engine/, models/, config/
ingest/ -> engine/, models/, config/
engine/ -> models/, config/
models/ -> (leaf -- no internal imports)
config/ -> (leaf -- no internal imports)
```

Enforced by `scripts/check_imports.py` in CI. Violations fail the build.

## Golden Principles (mechanically enforced)

Violations are caught by validate.sh. These are not suggestions.

1. **No secrets in code** -- use secret managers or env vars via config module.
2. **Structured logging only** -- `logger.info()` with correlation_id. Never `print()`.
3. **Module boundaries** -- enforced import DAG above.
4. **No God files** -- `scripts/check_architecture.py` flags files exceeding 300 lines.
5. **Type hints on all public functions** -- enforced by golden principles checker.
6. **No bare except** -- always catch specific exceptions.

## Boundaries

### Always (do without asking)

- Run `scripts/validate.sh` before committing
- Fix lint and format errors
- Update this file (AGENTS.md) when adding modules or commands
- Write tests for new code
- Use structured logging (no print/console.log)
- Follow the module dependency rules
- Add type hints to all public functions

### Ask First (propose and wait for approval)

- Adding new dependencies to pyproject.toml
- Changing public API contracts (query interface, CLI args)
- Adding new top-level modules under src/context_graph/
- Modifying CI workflows
- Changing the graph schema (node/edge types)
- Adding new external integrations

### Never (absolute prohibition)

- Delete existing tests
- Skip validate.sh or bypass pre-commit hooks
- Commit secrets, API keys, or credentials
- Push directly to main/master
- Disable linters or type checkers
- Import graph engine (kuzu) outside the engine/ module
- Use `print()` in production code
- Import os.environ outside config/ module

## Progressive Disclosure

| File | When to read |
|------|-------------|
| `docs/exec-plans/active/*.md` | Before implementing any task |
| `docs/product-specs/*.md` | Before building a feature |
| `docs/design-docs/*.md` | Before reopening a decision (ACCEPTED = locked) |
| `docs/QUALITY_SCORE.md` | When reviewing code |
| `docs/SECURITY.md` | When handling auth or secrets |
| `docs/RELIABILITY.md` | When handling errors, logging, retries |
| `docs/references/*.txt` | When using external APIs |

## Feature List

Features are tracked in `.harness/feature_list.json`. Each feature has `passes: true/false`.
- You may ONLY set `passes: true` after verifying the feature works end-to-end.
- You may NEVER remove features, edit descriptions, or change steps.
- Run `/features` to see current status.

## Standing Maintenance Orders

These trigger automatically during normal work:
1. **Module added** -> Update Module Dependency Rules section above
2. **Command added** -> Update Commands section above + all synced agent files
3. **Agent makes a mistake** -> Add a boundary rule to Boundaries section to prevent recurrence
4. **Architectural decision** -> Create a decision doc in `docs/design-docs/`
5. **Session start** -> Quick drift check: modules match reality, commands still work

## ExecPlans

Complex tasks (>30 min, multi-file, design decisions) require an ExecPlan.
See `PLANS.md` for the format. Active plans live in `docs/exec-plans/active/`.

## Git

Branch: `feature/<desc>`, `fix/<desc>`, `chore/<desc>`
Commit: `feat(scope):`, `fix(scope):`, `docs(scope):`, `chore(scope):`
PR: one concern per PR. `validate.sh` must pass first.
