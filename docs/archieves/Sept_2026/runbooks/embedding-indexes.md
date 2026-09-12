# Embedding Index Operations

Memoryhive stores vectors as portable JSON arrays behind an immutable embedding-index
schema. This is the currently approved `pgvector` equivalent because the supported
PostgreSQL 15 image does not include the extension, while JSON is supported by both
production PostgreSQL and SQLite validation environments. The retrieval layer must
filter by one `embedding_indexes.id`; it must never compare vectors across models,
dimensions, normalization modes, or index versions.

## Configure an index

Set all of the following on the backend, database worker, and Temporal worker:

```dotenv
AI_EMBEDDINGS_ROUTE=ollama:nomic-embed-text
AI_EMBEDDING_DIMENSIONS=768
AI_EMBEDDING_NORMALIZATION=l2
AI_EMBEDDING_INDEX_VERSION=1
AI_EMBEDDING_CHUNK_CHARACTERS=2000
AI_EMBEDDING_CHUNK_OVERLAP=200
AI_EMBEDDING_BACKFILL_BATCH_SIZE=25
AI_EMBEDDING_BACKFILL_MAX_ITEMS_PER_MINUTE=30
```

The route may instead select an explicitly configured Hugging Face,
OpenAI-compatible, or OpenRouter embedding model. An OpenRouter chat model alone
does not enable embeddings.

## Backfill existing content

After deploying the same settings to every worker, start the bounded workflow:

```bash
temporal workflow start \
  --type BackfillEmbeddingsWorkflow \
  --task-queue memoryhive-analysis \
  --workflow-id memoryhive-embedding-index-v1 \
  --input '{"expected_index_version":1,"max_items":1000,"items_per_minute":30}'
```

Use the Temporal UI query view to inspect `progress`, and monitor the existing AI
call, latency, token, cost, workflow-failure, and activity-failure metrics. Provider
budgets are reserved before every new vector call. Retries reuse the content hash;
resume a deliberately capped run by passing its returned `cursor` into a new input.

## Change model or dimension

1. Increase `AI_EMBEDDING_INDEX_VERSION` and change the model or dimension.
2. Deploy the new configuration everywhere before starting the migration workflow.
3. Use a unique workflow ID, such as `memoryhive-embedding-index-v2`.
4. Verify the committed Recall@K and latency gate and inspect provider cost/error
   metrics before making the new index eligible for retrieval.
5. Retain the prior index during rollout. Rollback means restoring the prior route,
   dimension, and version; no vector rows are rewritten in place.

The workflow rejects an `expected_index_version` that differs from the worker's
configuration. Item deletion immediately removes its chunks and vectors; account
deletion performs the same cleanup explicitly before removing the user.

## Future pgvector adoption

Adopt `pgvector` only after the extension image, migrations, backup/restore,
dimension migration, and rollback are exercised in staging. Keep the immutable
index registry and parallel-index rollout contract unchanged when replacing the
physical vector column.
