# Context Graph

> Keep in sync with AGENTS.md and .github/copilot-instructions.md.

## THE RULE

**`./scripts/validate.sh` must exit 0 before every commit. No exceptions.**

## Commands

```bash
./scripts/validate.sh              # Gate -- run before every commit
./scripts/boot_worktree.sh         # Boot locally (dynamic ports)
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

Enforced by `scripts/check_imports.py`. Violations fail the build.

## Golden Principles (mechanically enforced)

1. **No secrets in code** -- env vars via config module only.
2. **Structured logging only** -- `logger.info()` with correlation_id. Never `print()`.
3. **Module boundaries** -- enforced import DAG above.
4. **No God files** -- max 300 lines per file.
5. **Type hints on all public functions**.
6. **No bare except** -- catch specific exceptions.

## Boundaries

### Always (do without asking)
- Run `scripts/validate.sh` before committing
- Fix lint and format errors
- Update AGENTS.md when adding modules or commands
- Write tests for new code
- Use structured logging
- Follow module dependency rules

### Ask First
- Adding new dependencies
- Changing public API contracts
- Adding new top-level modules
- Modifying CI workflows
- Changing graph schema

### Never
- Delete existing tests
- Skip validate.sh or bypass hooks
- Commit secrets
- Push directly to main
- Import kuzu outside engine/
- Use print() in production code
- Import os.environ outside config/

## Progressive Disclosure

| File | When to read |
|------|-------------|
| `docs/exec-plans/active/*.md` | Before implementing any task |
| `docs/QUALITY_SCORE.md` | When reviewing code |
| `docs/SECURITY.md` | When handling auth or secrets |
| `docs/RELIABILITY.md` | When handling errors, logging |

## Feature List

Tracked in `.harness/feature_list.json`. Only set `passes: true` after verification.

## ExecPlans

Complex tasks require an ExecPlan. See `PLANS.md`. Active plans in `docs/exec-plans/active/`.
