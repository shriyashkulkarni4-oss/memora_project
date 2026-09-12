# Memoryhive backend

FastAPI service for Memoryhive's capture, retrieval, processing, and account APIs.

## Development

Install the locked development environment and run the validation suite:

```bash
uv sync --extra dev --locked
uv run ruff check app tests
uv run black --check app tests
uv run pytest -q
```

Run database migrations before starting the service against a persistent database:

```bash
uv run alembic upgrade head
```

The repository-level documentation describes local infrastructure, environment
configuration, and complete application startup workflows.
