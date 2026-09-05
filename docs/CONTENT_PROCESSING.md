# Content Processing

Memoryhive capture endpoints persist the item and a `processing_jobs` row in the
same database transaction. The API returns immediately. The independent worker
claims due jobs with PostgreSQL `FOR UPDATE SKIP LOCKED`, extracts content, and
updates the item revision so web and mobile clients receive the result through
normal refresh or incremental sync.

## Core Processors

- Screenshots are read from private object storage and processed by Tesseract.
- Links are resolved and fetched with redirect, content-size, and timeout limits.
- Link DNS answers must all be globally routable. Loopback, private, link-local,
  multicast, and reserved addresses are rejected on the initial URL and every
  redirect.
- Extracted text is whitespace-normalized, language-detected, and stored in both
  display and search-normalized fields.

Failed jobs use bounded exponential backoff and become terminal after three
attempts by default. A failed item remains intact and can be requeued with
`POST /api/v1/items/{item_id}/processing/retry`.

## Optional Enrichment

Core extraction does not depend on AI services. Set these variables only when
the corresponding service is available:

```env
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
N8N_WEBHOOK_URL=http://n8n:5678/webhook/memoryhive
N8N_API_KEY=
```

Ollama can add a short summary. The n8n response may include `summary`, `tags`,
and `classification`. Adapter failures are logged and never fail successful OCR
or link extraction.

## Operations

```bash
docker compose run --rm backend alembic upgrade head
docker compose up -d backend worker
docker compose logs -f worker
```

The worker recovers jobs left in `processing` for more than ten minutes. Queue
depth and failed jobs can be inspected directly:

```sql
SELECT status, count(*) FROM processing_jobs GROUP BY status;
SELECT id, item_id, attempts, last_error
FROM processing_jobs WHERE status = 'failed' ORDER BY updated_at DESC;
```
