# Dunning IQ — API

FastAPI backend for Dunning IQ. See the [top-level README](../README.md) for the full picture.

```bash
uv sync
uv run alembic upgrade head
uv run python -m app.seed.run        # seed demo data
uv run uvicorn app.main:app --reload --port 8000
```
