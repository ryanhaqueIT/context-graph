# Context Graph -- Copilot Instructions

Run `./scripts/validate.sh` before every commit. No exceptions.

## Commands
- Lint: `ruff check .` (from src/context_graph/)
- Format: `ruff format .` (from src/context_graph/)
- Test: `python -m pytest tests/`
- Type check: `pyright`
- Full gate: `./scripts/validate.sh`

## Module Rules
cli -> engine, query, ingest, config, models
query -> engine, models, config
ingest -> engine, models, config
engine -> models, config
models -> (leaf)
config -> (leaf)

## Never
- Import kuzu outside engine/
- Use print() in production code
- Import os.environ outside config/
- Delete tests
- Skip validate.sh
