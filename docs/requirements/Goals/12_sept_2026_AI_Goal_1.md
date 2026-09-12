# Memoryhive AI Goal 1

Date: 12 September 2026  
Status: Implementation complete — production enablement remains gated
Scope: AI extraction, model connectivity, Temporal reliability, monitoring,
AI-powered recall, administration, privacy, testing, and production readiness

## Terminology

The requested phrase “OpenAPI compatible” is interpreted in this document as
**OpenAI-compatible API**. OpenAPI is an API-description standard; OpenAI-compatible
describes model endpoints that implement contracts such as `/v1/chat/completions`,
`/v1/embeddings`, or `/v1/responses`.

The generic OpenAI-compatible adapter is deliberately the last provider adapter
in the implementation sequence. It will support configurable services such as
OpenAI, DeepSeek, vLLM, LM Studio, and other compatible gateways without treating
their capabilities as identical.

## Goal

Turn Memoryhive’s current OCR, link extraction, optional Ollama summary, n8n
webhook, and Temporal scaffold into a reliable and observable AI enrichment and
personal-recall platform.

The result must:

- preserve instant, offline-first capture;
- work without any external AI provider;
- support Ollama, OpenRouter, Hugging Face Inference Providers, n8n, and a generic
  OpenAI-compatible endpoint;
- make provider use, fallbacks, model output, latency, cost, and errors observable;
- make Temporal execution visible and operationally supportable;
- add hybrid semantic retrieval, useful organization, related memories, and
  explainable resurfacing;
- never silently move private user content between AI providers;
- provide measurable quality gates before AI features are presented as an AI moat.

## Current Baseline

Memoryhive already provides:

- link, screenshot, and text capture;
- Tesseract OCR, language detection, normalization, and public-link extraction;
- optional Ollama summarization and n8n enrichment;
- deterministic extractive-summary fallback;
- PostgreSQL keyword/full-text search across extracted content;
- an optional version-aware Temporal workflow with retries;
- item analysis states and aggregate pending/failed counts;
- legacy processing-job inspection and retry;
- API request metrics, three Prometheus alerts, structured logs, and process health
  checks;
- web/mobile summary display and offline mobile synchronization.

Important gaps in the baseline:

- text captures and edited content can remain `pending` when Temporal is disabled;
- Temporal is not tested end to end;
- the Admin UI does not show Temporal executions or AI runs;
- Prometheus does not scrape Temporal or worker/AI metrics;
- optional model failures are swallowed and reported as successful fallback output;
- n8n tag suggestions and classification are stored only as metadata;
- no OpenRouter, Hugging Face, or generic OpenAI-compatible mechanism exists;
- no embeddings, semantic retrieval, reranking, related-item discovery, provenance,
  prompt versioning, feedback, evaluation, or budget controls exist.

## Architectural Principles

1. Capture must never wait for AI.
2. Deterministic extraction and OCR remain useful without a model.
3. Temporal orchestrates durable analysis; provider adapters do not own workflow
   state.
4. One analysis state machine is shared by Temporal and the database-worker
   fallback.
5. Provider fallback is explicit policy, not an automatic surprise.
6. Raw user content and credentials are never written to metrics or normal logs.
7. Structured output is validated before it changes user-visible data.
8. Generated data records provider, model, prompt version, source, time, and
   fallback provenance.
9. AI suggestions remain reversible and distinguishable from user-authored data.
10. Quality, latency, cost, and privacy are release gates, not post-release ideas.

## Delivery Sequence

| Phase | Outcome | Tasks |
| --- | --- | --- |
| 0 | Correct and dependable analysis lifecycle | AI-001 to AI-003 |
| 1 | Provider-neutral model foundation | AI-004 to AI-009 |
| 2 | Observable Temporal and AI operations | AI-010 to AI-013 |
| 3 | AI product features and moat | AI-014 to AI-019 |
| 4 | Evaluation, privacy, rollout, and production proof | AI-020 to AI-023 |

## Execution Tracker

This table is the authoritative implementation queue. A task may move to
`Completed` only after its acceptance criteria and validation evidence have been
recorded in its section. Tasks are executed in numeric order.

| Task | Status | Completed | Evidence |
| --- | --- | --- | --- |
| AI-001 | Completed | 2026-09-12 | Migration 009, transactional dispatch service, Temporal/database dispatch integration, lifecycle regression suite |
| AI-002 | Completed | 2026-09-12 | Versioned provider-neutral contracts, split extraction/enrichment stages, Temporal serialization and validation regression suite |
| AI-003 | Completed | 2026-09-12 | Migration 010, checkpointed multistage workflow, cancellation API, controlled backfill workflow, execution and replay tests |
| AI-004 | Completed | 2026-09-12 | Provider-neutral gateway, normalized errors/usage/provenance, Ollama/n8n adapters, shared conformance suite |
| AI-005 | Completed | 2026-09-12 | First-class OpenRouter chat/embedding/catalog adapter, allowlisted routing, provenance, admin health API, failure suite |
| AI-006 | Completed | 2026-09-12 | Hugging Face router chat and native feature-extraction adapter, scoped allowlists/policies, health and failure suites |
| AI-007 | Completed | 2026-09-12 | Structured Ollama chat/embeddings/model health plus versioned and signed n8n contract with production auth validation |
| AI-008 | Completed | 2026-09-12 | Restricted OpenAI-compatible Chat/Responses/Embeddings adapter, SSRF/header/redirect controls, four-vendor fixtures |
| AI-009 | Completed | 2026-09-12 | Migration 011, immutable task routing, privacy/fallback controls, database budgets, redacted admin config, secret-safe Compose/Kubernetes and store checks |
| AI-010 | Completed | 2026-09-12 | Migration 012, privacy-safe AI run recorder, field provenance, admin run API, export and account-deletion coverage |
| AI-011 | Completed | 2026-09-12 | Migration 013, bounded API/dispatch/queue/worker/Temporal/provider metrics, SDK exporter, correlation propagation, Prometheus scrape configuration |
| AI-012 | Completed | 2026-09-12 | Generated observability profile, five provisioned Grafana dashboards, 16 owned alerts, Alertmanager routing, runbook and promtool synthetic drills |
| AI-013 | Completed | 2026-09-12 | Migration 014, content-safe operations API/UI, Temporal correlation/link, provider health, confirmed idempotent retry/cancel/reanalyze with operator audit |
| AI-014 | Completed | 2026-09-12 | Migration 015, provider-independent grounded enrichment normalization, versioned taxonomy/tag matching, durable tenant-scoped history, field provenance and golden quality fixtures |
| AI-015 | Completed | 2026-09-12 | Migration 016, immutable private feedback/preferences, reversible revision-safe APIs, confidence-gated auto-apply, web/mobile review UI and offline conflict replay |
| AI-016 | Completed | 2026-09-12 | Migration 017, stable versioned chunks, immutable parallel embedding indexes, provider-neutral reuse pipeline, bounded Temporal backfill, deletion/export lifecycle and Recall@K/latency corpus |
| AI-017 | Completed | 2026-09-12 | Tenant-filtered keyword/semantic candidate retrieval, deterministic weighted RRF, exact boosts, passage explanations, bounded Ollama reranking, AI-off fallback and Recall@K/NDCG/latency gates |
| AI-018 | Completed | 2026-09-12 | Migration 018, exact/semantic duplicate suggestions, explainable related memories, diverse frequency-capped resurfacing, append-only reversible feedback, web and offline-mobile surfaces |
| AI-019 | Completed | 2026-09-12 | Owner-scoped single-turn recall, server-verified claim citations, insufficient-evidence fallback, provider policy/budgets, web UI, independently gated rollout |
| AI-020 | Completed | 2026-09-12 | Versioned consent-safe corpus, 19 quality/operations metrics, blocking floors, baseline trends, credential-free CI report and opt-in capped live probes |
| AI-021 | Completed | 2026-09-12 | Real Temporal API/history acceptance, deterministic recovery/provider failures, capture-burst/backlog/search load gate, AI browser flows, sanitized failure artifacts, separated CI lanes |
| AI-022 | Completed | 2026-09-12 | Default-off user consent, local/external route enforcement at dispatch and execution, governance/provider register, secret/SSRF/privacy/store/deletion controls and regression coverage |
| AI-023 | Completed | 2026-09-12 | Independent rollout/provider flags, shadow ranking, pausable bounded backfill, SLO/cost/ownership policy, go-no-go evidence validator, Compose/Kubernetes matrix validation |

---

## AI-001 — Repair Analysis Dispatch and State Transitions

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added migration `009_analysis_dispatch.py`, extending `processing_jobs` into a
  transactional analysis-dispatch outbox with analysis version, selected
  execution backend, dispatch reason, Temporal workflow ID, and a unique
  item/version invariant.
- Added `app/services/analysis_dispatch.py` as the single entry point for capture,
  content-edit, manual/admin retry, and pending-item backfill dispatch.
- Link, screenshot, and text captures now persist scheduling intent in the same
  transaction as the item. Content edits create a new version; favorite, archive,
  category, and tag changes do not.
- The database worker now processes text items, filters work by its assigned
  backend, recovers stale claims, and skips stale analysis versions.
- The Temporal scheduler now consumes the same outbox, records workflow IDs, and
  transitions items through `scheduled` before activity execution.
- Added `scheduled` and `degraded` analysis states. Configured enrichment failure
  now produces a visible degraded outcome while preserving deterministic results.
- Added a terminal Temporal failure activity so exhausted activity retries cannot
  leave an item indefinitely analyzing.
- Added note context to enrichment requests and preserved user-authored fields.
- Existing screenshots cannot replace their source asset through the current API;
  every supported screenshot-source creation path now dispatches analysis. Any
  future asset-replacement endpoint must use the same dispatch service.

Validation evidence:

- Backend Ruff and Black checks pass.
- Full backend suite: `41 passed`.
- Focused lifecycle, migration, API, admin, and processing suite: `27 passed`.
- Frontend: ESLint, `17` Vitest tests, and production build pass.
- Mobile: TypeScript, Expo lint, and `61` Vitest tests pass.
- Migration upgrade-to-head and downgrade-to-base are covered by the passing
  backend migration test.

### Problem

The default database worker does not analyze text captures, and content edits mark
items pending without always creating work. Analysis state can therefore diverge
from actual executable work.

### Task

Create one analysis-dispatch service used by create, screenshot upload, edit,
retry, backfill, and administrative reanalysis flows.

### Description

- Define an explicit state machine: `not_analyzed`, `pending`, `scheduled`,
  `analyzing`, `analyzed`, `degraded`, `failed`, and `skipped`.
- Add `degraded` for successful deterministic extraction when optional AI failed
  or was unavailable.
- Ensure text, link, and screenshot captures all create executable analysis work.
- Ensure material edits increment `analysis_version` and schedule the new version.
- Do not reanalyze for favorite, archive, category, or user-tag-only changes.
- Use a transactional outbox or equivalent database record so item persistence and
  scheduling intent cannot become inconsistent.
- Make dispatch select Temporal or the database-worker fallback from one policy.
- Ensure old versions cannot overwrite current item data.

### Acceptance Criteria

- Every new item reaches a terminal analysis state with Temporal both enabled and
  disabled.
- Updating URL, raw text, screenshot source, or analysis-relevant notes schedules
  exactly one new analysis version.
- Non-content changes do not schedule analysis.
- A process crash after database commit cannot lose scheduling intent.
- Duplicate dispatch is idempotent.
- Regression tests cover all item types, both dispatch modes, duplicate delivery,
  stale versions, retries, and crash recovery.

### AI Notes

The provider must not be called from API request handlers. Provider selection is
captured with the work request so a retry does not unexpectedly change vendor.

## AI-002 — Establish One Canonical Analysis Contract

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added `app/ai/contracts.py` with versioned, provider-neutral contracts for
  extraction, enrichment, deterministic chunking, embeddings, final analysis,
  and indexing.
- Split `ContentProcessor` into explicit deterministic extraction and optional
  enrichment stages. Both Temporal activities and the database worker continue
  through the same `run_item_analysis` path and canonical contracts.
- Changed the workflow wire representation of item type to a validated plain
  string after a Temporal converter regression test exposed unsafe round-tripping
  of the string-backed enum.
- Provider output is constructed and validated as a complete immutable
  `EnrichmentResult` before it can affect an `AnalysisResult`; malformed, empty,
  or refused output leaves the deterministic fallback intact and records a
  degraded enrichment result.
- Added deterministic content bounds and stable Unicode-safe chunks with content
  hashes, offsets, analysis versions, and stable chunk IDs. Embedding contracts
  reject dimension drift and non-finite vectors.
- Final persistence continues to preserve user-authored title, description,
  notes, category, and tags, while stale-version guards prevent obsolete results
  from being applied.

Validation evidence:

- Backend Ruff and Black checks pass.
- Focused contract, processing, dispatch, and analysis suite: `25 passed`.
- Full backend suite: `50 passed`.
- Tests cover Temporal converter round-tripping, immutable/deterministic
  contracts, schema limits, empty and large content, Unicode, malformed output,
  empty/refused enrichment, stale versions, and embedding validation.

### Problem

Extraction, enrichment, persistence, and analysis status are coupled inside the
current content processor, making provider expansion and provenance difficult.

### Task

Split deterministic extraction from AI enrichment and define versioned input and
output contracts.

### Description

- Create separate stages for acquisition, extraction, chunking, enrichment,
  embedding, persistence, and indexing.
- Define typed contracts such as `ExtractionInput`, `ExtractedDocument`,
  `EnrichmentRequest`, `EnrichmentResult`, `EmbeddingRequest`, and
  `EmbeddingResult`.
- The enrichment result should support summary, topics, suggested tags,
  classification, entities, key phrases, confidence, warnings, and provenance.
- Store contract and schema versions.
- Limit content by deterministic truncation/chunking policies rather than by
  provider-specific slicing embedded in adapters.
- Preserve user-entered title, description, notes, category, and tags.

### Acceptance Criteria

- The same contracts are used by Temporal activities and the legacy worker.
- Invalid or incomplete provider responses cannot partially mutate an item.
- Contract serialization is deterministic and Temporal replay-safe.
- Unit tests cover schema validation, empty content, large content, Unicode,
  provider refusal, malformed JSON, and stale item versions.

### AI Notes

Use schema-constrained JSON when a provider supports it, but always validate
locally. Providers lacking strict structured output must use a parse-and-repair
boundary with bounded retries.

## AI-003 — Expand the Temporal Workflow

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added migration `010_analysis_stages.py` and durable job checkpoints for stage
  data, content hash, current stage, and cancellation intent.
- Replaced the opaque new-workflow path with separately visible extraction,
  enrichment, chunk/embedding, persistence, and indexing activities. Each has a
  bounded timeout and stage-appropriate retry policy; long extraction and chunk
  work heartbeat.
- Activities pass only job/item identifiers and version through workflow history.
  Extracted content and intermediate results remain in versioned database
  checkpoints, allowing enrichment and later stages to retry without repeating
  successful OCR or link acquisition.
- Every stage is idempotent. Repeated extraction uses its content-hash checkpoint,
  and repeated persistence cannot increment item revision or duplicate visible
  data.
- Added an authenticated item cancellation endpoint and workflow signal. A
  cancellation finishes the current idempotent activity, stops before the next
  stage, and leaves the item pending with an explicit retryable explanation.
- Added `BackfillAnalysisWorkflow` with bounded child workflows, rate limiting,
  `pause`, `resume`, and `cancel` signals, and a `progress` query.
- Added optional custom Temporal visibility attributes for hashed tenant, item
  type, analysis version, provider, model, stage, and outcome, plus an idempotent
  setup command in `app.temporal_pipeline.setup`.
- Added the `analysis-multistage-v1` patch marker, configurable worker build ID,
  a 30-day retention policy setting/runbook, and a fail-closed production payload
  encryption requirement. The compatibility activity remains registered for old
  histories until their retention window expires.

Validation evidence:

- Backend Ruff and Black checks pass.
- Focused Temporal workflow/checkpoint/dispatch suite: `13 passed`.
- Full backend suite, including migration upgrade/downgrade: `57 passed`.
- Real ephemeral Temporal execution tests verify independent activity order,
  rate-limited child workflows, cancellation signaling, and successful replay of
  captured workflow history.
- Temporal sandbox validation passes for analysis and backfill workflows.
- Frontend ESLint, `17` Vitest tests, TypeScript build, and Vite production build
  pass after the expanded admin job contract.

### Problem

The current workflow is one ten-minute activity. It provides retries but not
stage visibility, selective retry, independent timeouts, or controlled backfill.

### Task

Implement a multi-stage, versioned `AnalyzeItemWorkflow` and supporting
maintenance workflows.

### Description

- Split extraction, enrichment, embedding, and persistence into activities.
- Give each activity an appropriate timeout, retry policy, and non-retryable error
  classification.
- Add heartbeats for OCR, large-document processing, and batch operations.
- Add workflow search attributes for item type, user-safe tenant identifier,
  analysis version, provider, model, stage, and outcome.
- Add signals or safe API operations for cancel and retry.
- Add a rate-limited `BackfillAnalysisWorkflow` using child workflows or bounded
  batches.
- Define workflow versioning/build-ID strategy for compatible deployments.
- Define retention and payload-codec/encryption requirements for sensitive data.

### Acceptance Criteria

- Temporal UI shows each analysis stage and its retries independently.
- Retrying enrichment does not repeat successful OCR or public-link extraction.
- Cancelling a workflow leaves the item in a consistent recoverable state.
- Worker restart during every stage resumes without duplicate user-visible data.
- A controlled backfill can be paused, resumed, rate-limited, and audited.
- Replay tests pass for committed workflow histories.

### AI Notes

Prefer passing item IDs, versions, and content hashes through workflow history.
Load sensitive document content inside activities so raw personal content is not
unnecessarily persisted in Temporal event history.

---

## AI-004 — Introduce the Provider Gateway

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added a provider-neutral gateway with explicit provider and capability enums
  for Ollama, OpenRouter, Hugging Face, n8n, and OpenAI-compatible services;
  enrichment, embeddings, vision, model listing, usage, and health are distinct
  interfaces rather than a generic HTTP escape hatch.
- Added the complete normalized error taxonomy, with retryability encoded by
  error class. Authentication, authorization, invalid requests, malformed
  responses, refusals, unsupported operations, budget failures, and open
  circuits are never retried; rate limits, timeouts, and unavailability use
  bounded exponential backoff with jitter.
- Added shared enforcement for provider concurrency, timeouts, UTF-8 payload
  bytes, maximum attempts, and circuit breaking, backed by validated and
  environment-configurable limits.
- Added normalized token/cost usage, request ID, latency, provider, and model
  provenance contracts on successful responses.
- Moved Ollama and n8n HTTP behavior into dependency-injected adapters and a
  composition factory. Content analysis now uses only gateway operations and
  locally validated canonical enrichment results.
- HTTP status mapping and unknown adapter failures are converted to sanitized
  provider errors. Response bodies, authorization headers, and credential values
  are not included in errors, logs, API results, or Temporal inputs.
- Capability and payload validation occurs before an adapter is invoked, so an
  incompatible or oversized request cannot schedule a provider call.

Validation evidence:

- Backend Ruff and Black checks pass.
- Gateway tests cover retry selection and delay bounds, preflight rejection,
  payload bounds, circuit opening, unknown-error sanitization, normalized HTTP
  status mapping, usage, and provenance.
- Ollama and n8n pass the same mock-transport conformance assertions.
- Full backend suite: `67 passed`.

### Problem

Ollama and n8n calls are hard-coded in the content processor. There is no common
capability model, response provenance, configuration validation, or consistent
error taxonomy.

### Task

Create a provider-neutral AI gateway with task-specific interfaces.

### Description

- Define provider types: `ollama`, `openrouter`, `huggingface`, `n8n`, and
  `openai_compatible`.
- Define independent capabilities for chat/structured enrichment, embeddings,
  vision, model listing, token usage, and health validation.
- Define normalized errors: authentication, authorization, rate limit, timeout,
  unavailable, invalid request, unsupported capability, malformed response,
  content refusal, and budget exceeded.
- Add bounded retries with jitter only for retryable errors.
- Add per-provider concurrency, timeout, payload-size, and circuit-breaker limits.
- Return normalized usage and provenance with every response.
- Keep adapters dependency-injected and independently testable with mock HTTP
  transports.

### Acceptance Criteria

- Analysis code depends only on gateway contracts, not provider-specific HTTP.
- Provider credentials never appear in exceptions, logs, API responses, or
  Temporal payloads.
- Capability negotiation rejects incompatible task/model combinations before
  scheduling expensive work.
- All provider adapters pass a shared conformance test suite.

### AI Notes

Do not reduce the gateway to one generic HTTP function. Shared wire formats do
not guarantee shared support for JSON schemas, embeddings, usage, model listing,
vision, reasoning fields, or error behavior.

## AI-005 — Implement OpenRouter Connectivity

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added an opt-in OpenRouter adapter for `/chat/completions`, `/embeddings`, and
  `/models`, using bearer authentication plus optional `HTTP-Referer` and
  `X-Title` attribution headers.
- Enrichment requests use the canonical Memoryhive JSON Schema, low configurable
  temperature, bounded output tokens, prompt-injection-resistant system context,
  and locally validated results.
- Configuration requires an API key, default model, and explicit model allowlist.
  Embedding models use the same allowlist, and no UI-supplied arbitrary model or
  provider identifier reaches the adapter.
- Provider routing records the configured provider order/restriction,
  `allow_fallbacks`, required-parameter policy, and data-collection policy.
  Fallback defaults off and a fallback to a non-primary underlying provider is
  explicit in persisted provenance.
- Results capture configured and resolved model, resolved provider, finish reason,
  request/generation ID, latency, token counts, and returned cost.
- Added a no-user-content model-catalog health probe and an admin-only
  `/api/v1/admin/ai/providers/health` surface shared by all configured providers.
- OpenRouter remains entirely absent from the gateway and makes no request unless
  `OPENROUTER_ENABLED=true`; production-safe examples keep it disabled until
  credentials and allowlists are supplied.
- The embedding implementation follows OpenRouter's documented
  `/api/v1/embeddings` contract and validates returned vector dimensions before
  accepting it.

Validation evidence:

- Backend Ruff and Black checks pass.
- Tests cover schema-valid enrichment, structured request shape, attribution
  headers, model/provider allowlists, disabled behavior, missing configuration,
  invalid key, rate limiting, budget exhaustion, timeout, malformed JSON,
  refusal, provider fallback, embedding dimensions, usage/cost, and content-free
  health checks.
- The admin health endpoint is verified as admin-only.
- Full backend suite: `79 passed`.

### Problem

Memoryhive cannot currently use OpenRouter’s model catalog or routing controls.

### Task

Add a first-class OpenRouter adapter for enrichment and supported embedding tasks.

### Description

- Use the OpenRouter `/api/v1/chat/completions` contract.
- Support API key, model slug, optional application attribution headers, timeout,
  maximum tokens, temperature, structured-output options, and routing policy.
- Support an allowlist of models and providers; do not allow arbitrary UI-supplied
  model IDs in production.
- Capture the requested model, resolved model/provider when returned, token usage,
  finish reason, latency, request ID, and estimated/returned cost metadata.
- Implement startup/configuration validation and a non-content-bearing health
  probe.
- Make OpenRouter-side provider fallback opt-in and visible in provenance.
- Validate OpenRouter errors and rate-limit headers into the common error model.

### Acceptance Criteria

- A configured OpenRouter model can produce a schema-valid Memoryhive enrichment.
- Invalid key, missing model, rate limit, timeout, malformed response, refusal, and
  provider fallback are covered by tests.
- The Admin health surface can validate connectivity without sending user content.
- Every OpenRouter result records both configured routing policy and resolved
  provider/model where available.
- Disabling OpenRouter prevents all outbound calls to it.

### AI Notes

OpenRouter documents an OpenAI-compatible chat endpoint and optional routing
across many models. Provider routing must be constrained for privacy, residency,
quality, and predictable cost. Reference:
[OpenRouter quickstart](https://openrouter.ai/docs/quickstart) and
[chat API reference](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request?explorer=true).

## AI-006 — Implement Hugging Face Connectivity

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added an opt-in Hugging Face Inference Providers adapter using the documented
  OpenAI-compatible `router.huggingface.co/v1/chat/completions` path for
  structured chat enrichment.
- Added native HF Inference feature extraction via the documented
  `/hf-inference/models/{model}/pipeline/feature-extraction` task route, including
  normalized/truncated input and strict expected-dimension validation.
- Implemented and validated `:fastest`, `:cheapest`, `:preferred`, and explicitly
  allowlisted named-provider suffixes. The base model plus effective policy or
  provider are recorded in result provenance.
- Added separate chat, embedding, and vision allowlists. Chat and embedding
  capabilities are advertised only when their corresponding allowlists are
  configured, preventing cross-task model use.
- Chat responses pass through the same canonical structured enrichment schema and
  capture requested/resolved model, selected provider when returned, routing
  policy, finish reason, usage, request ID, and latency.
- Added catalog and Hub-metadata health validation that sends no user content and
  verifies the configured chat model and embedding pipeline capability.
- Hugging Face is explicitly opt-in. Tokens are represented as secrets, sent only
  as bearer authorization, never logged, and require only the fine-grained “Make
  calls to Inference Providers” permission; the application performs no Hub write
  operations.

Validation evidence:

- Backend Ruff and Black checks pass.
- Tests cover schema-valid chat, all supported policy/provider suffixes,
  feature-extraction request shape, stable dimensions, dimension drift, cold
  models, unavailable providers, authentication, rate limiting, malformed
  output, unknown providers, metadata-only health, missing configuration, and
  disabled outbound behavior.
- Full backend suite: `93 passed`.

### Problem

Memoryhive cannot use hosted open models or Hugging Face Inference Providers for
enrichment and embedding workloads.

### Task

Add a first-class Hugging Face adapter supporting chat and non-chat inference
capabilities required by Memoryhive.

### Description

- Support the Hugging Face router with a fine-grained token.
- Use the OpenAI-compatible chat endpoint for chat enrichment where appropriate.
- Use the Hugging Face inference client/native task contract for feature
  extraction/embeddings when chat compatibility is insufficient.
- Support model IDs with explicit provider or policy suffixes such as fastest,
  cheapest, preferred, or a named inference provider.
- Add model/capability validation using model metadata where available.
- Record the requested model, selected inference provider, policy, usage, latency,
  and response metadata.
- Maintain separate allowlists for chat, embedding, and vision models.

### Acceptance Criteria

- A configured Hugging Face chat model produces a schema-valid enrichment.
- A configured feature-extraction model returns embeddings with stable expected
  dimensions.
- Provider/policy suffix handling is tested.
- Cold model, unavailable provider, authentication, rate-limit, dimension change,
  and malformed-output cases are tested.
- Tokens use only the minimum required inference permission.

### AI Notes

Hugging Face’s OpenAI-compatible endpoint is primarily a chat interface; native
inference clients remain necessary for tasks such as feature extraction. Reference:
[Inference Providers](https://huggingface.co/docs/inference-providers/en/index)
and [inference client guidance](https://huggingface.co/docs/huggingface_hub/en/guides/inference).

## AI-007 — Harden and Retain Ollama and n8n

Status: **Completed — 2026-09-12**

Implementation evidence:

- Upgraded Ollama enrichment from free text to the canonical JSON Schema via its
  native structured-output `format` field, deterministic temperature, and
  configurable `keep_alive` control.
- Added Ollama `/api/embed` support with an explicit embedding model, expected
  dimensions, normalized usage, and local/self-hosted/third-party deployment
  provenance.
- Ollama health now validates that both configured chat and embedding models are
  actually present in `/api/tags`; an empty catalog is visible as unavailable,
  never as a successful AI service.
- Versioned the n8n request and response contract. Requests include item and
  analysis version, canonical schema version, language, and content; responses
  with a missing or changed schema version are rejected atomically.
- Added optional HMAC-SHA256 webhook signing over timestamp plus canonical UTF-8
  JSON, alongside existing bearer authentication. Deployment provenance records
  whether the automation is local, self-hosted, or third-party.
- Production settings reject unauthenticated external n8n webhook URLs. Internal
  endpoints can remain network-authenticated, while external endpoints require a
  bearer key or signing secret.
- Deterministic extraction/summary fallback remains the terminal degraded result
  when Ollama and n8n are disabled or unavailable.

Validation evidence:

- Backend Ruff and Black checks pass.
- Ollama and n8n continue to pass the shared provider conformance suite.
- Dedicated tests cover structured output, schema and keep-alive request shape,
  embeddings, model outage health, signed canonical requests, schema drift,
  deployment provenance, and production external-webhook authentication.
- Full backend suite: `98 passed`.

### Problem

Existing Ollama/n8n integrations lack structured contracts, provenance, explicit
health, consistent errors, and operational metrics.

### Task

Move Ollama and n8n behind the provider gateway and make their behavior equivalent
to other supported providers.

### Description

- Add Ollama model availability checks, structured JSON output where supported,
  keep-alive controls, and embedding capability.
- Define and version the n8n request/response contract.
- Require n8n authentication in staging/production.
- Add webhook signing or a request signature where the deployed n8n workflow can
  support it.
- Record whether output is local, self-hosted, or third-party.
- Preserve deterministic fallback if neither provider is enabled.

### Acceptance Criteria

- Ollama and n8n pass the shared provider conformance suite.
- A model outage produces a visible degraded result rather than a false AI success.
- n8n schema drift is rejected without corrupting item metadata.
- Production validation rejects an unauthenticated external n8n endpoint.

### AI Notes

Ollama is the preferred privacy-preserving baseline. n8n should orchestrate
external automation where useful, but it should not become the canonical store
of analysis state.

## AI-008 — Implement the Generic OpenAI-Compatible Adapter Last

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added the generic adapter only after OpenRouter and Hugging Face, and kept it
  last in the enrichment candidate order.
- Supports explicitly selected Chat Completions or Responses mode. Embeddings,
  model listing, usage, and health exist only when the operator declares the
  corresponding capability; nothing is inferred from a URL or model name.
- Added separate chat/embedding allowlists, bounded output controls, optional API
  key, deployment classification, and a small allowlist of compatibility options.
  Security-sensitive headers (`Authorization`, API keys, cookies, host, proxy
  authorization, and transfer encoding) cannot be overridden.
- Requires an exact operator host allowlist. URL credentials, queries, fragments,
  metadata hosts, loopback, link-local, and private IPs are rejected. DNS results
  are checked before calls to resist hostname rebinding; private vLLM/LM Studio
  hosts require both network opt-in and an exact private-host allowlist.
- Redirect following is forcibly disabled even when an injected HTTP client was
  configured to follow redirects, preventing authorization from reaching a new
  host.
- OpenAI, DeepSeek, vLLM, and LM Studio are configuration examples over the same
  contract. DeepSeek requires no service-specific analysis code.
- Compatible Chat/Responses results use the canonical structured enrichment
  boundary; embedding vectors retain strict dimension validation.

Validation evidence:

- Backend Ruff and Black checks pass.
- Mock contract fixtures pass for OpenAI, DeepSeek, vLLM, and LM Studio.
- Tests cover both endpoint modes, independently flagged embeddings, dimension
  drift, unapproved and private hosts, explicit private-host operation, metadata
  and link-local blocking, forbidden header override, unsupported mode,
  incompatible response, and cross-host redirect prevention.
- Full backend suite: `111 passed`.

### Problem

Operators need connectivity to OpenAI-compatible services such as OpenAI,
DeepSeek, vLLM, LM Studio, or private gateways without adding a bespoke adapter
for every service.

### Task

After OpenRouter and Hugging Face are stable, add a restricted generic
OpenAI-compatible adapter.

### Description

- Configure base URL, API key, model, endpoint mode, timeout, optional headers,
  output limits, and declared capabilities.
- Support Chat Completions first; add Responses and Embeddings only behind
  separately tested capability flags.
- Require an operator allowlist for base URL hosts in staging/production.
- Block loopback, link-local, metadata, and private destinations unless an explicit
  self-hosted-network setting permits a validated host.
- Never infer provider capabilities solely from the base URL.
- Add named configuration examples for OpenAI, DeepSeek, vLLM, and LM Studio, but
  store them through the same generic contract.
- Allow provider-specific compatibility options only in a bounded extension map.

### Acceptance Criteria

- Contract tests pass against mock OpenAI, DeepSeek, vLLM, and LM Studio response
  fixtures.
- The adapter rejects an unapproved host, unsupported endpoint mode, changed
  embedding dimension, and non-compatible response.
- DeepSeek can be selected by base URL and model without DeepSeek-specific code in
  analysis services.
- A generic endpoint cannot override security-sensitive headers or send secrets to
  a redirected host.

### AI Notes

DeepSeek documents OpenAI-compatible base URLs and SDK usage, but compatibility
features vary by model and endpoint. Reference:
[DeepSeek API call guide](https://api-docs.deepseek.com/guides/function_calling)
and [DeepSeek Responses API](https://api-docs.deepseek.com/api/create-response/).

## AI-009 — Add Provider Policy, Configuration, and Secret Management

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added explicit policy resolution for summarization, structured enrichment,
  embeddings, reranking, and vision. Every configured task validates provider
  availability and capability and resolves its provider/model before dispatch.
- Migration `011_ai_policy_usage.py` captures the selected primary route and
  immutable fallback policy on each analysis job and adds database-backed AI
  usage reservations for request, token, estimated-cost, and per-user limits.
- Cross-provider fallback is disabled by default. When enabled, ordered fallback
  routes are captured with the job and successful fallback output records
  `gateway_fallback` provenance.
- External providers require both an explicit content-transfer opt-in and a
  provider allowlist entry. Invalid, unavailable, unsafe, or negative-budget
  configurations fail closed before model execution.
- Added a system credential-reference contract whose opaque scope/reference
  design supports future per-user BYOK without placing plaintext credentials in
  job, API, or audit payloads.
- Added an admin-only AI configuration endpoint exposing task routes, safe
  budget/privacy controls, deployment class, and credential-presence booleans;
  credentials, endpoint URLs, headers, and secret values are never returned.
- Added all provider, routing, fallback, and budget settings to environment
  templates and generated Compose profiles. Kubernetes manifests retain safe
  disabled defaults while optional operator settings and credentials are streamed
  directly to Secret resources and are never persisted in generated manifests.
- Extended mobile store disclosure resolution to detect Ollama, n8n, OpenRouter,
  Hugging Face, generic OpenAI-compatible providers, and explicit task routes
  without copying provider endpoints or credentials into release artifacts.

Validation evidence:

- Backend Ruff and Black checks pass; full backend suite: `119 passed`.
- Policy tests cover all five task types, capability rejection, embedding model
  resolution, immutable dispatch policy, privacy consent, opt-in fallback and
  provenance, future BYOK references, global/per-user request and token limits,
  cost limits, usage persistence, and deterministic budget degradation.
- Compose generation and validation pass with `29` build-project tests.
- Kubernetes validation passes for all 12 environment/profile combinations;
  deployment tests prove all provider secrets are streamed and absent from
  committed manifests.
- Mobile TypeScript and lint pass; full mobile suite: `65 passed`, including
  provider-family store-disclosure mismatch tests.

### Problem

A list of API keys is not a safe routing strategy. Memoryhive needs explicit
task-level provider selection, privacy controls, budgets, and deployment-safe
configuration.

### Task

Implement configuration and policy for provider routing without exposing secrets
to clients.

### Description

- Configure independent primary providers/models for summarization, structured
  enrichment, embeddings, reranking, and vision.
- Define an ordered fallback policy per task, disabled by default.
- Record whether content may leave the deployment and which provider classes are
  allowed.
- Support system-wide settings first; design data contracts so per-user BYOK can
  be added later without storing plaintext credentials.
- Add environment variables and secret references to Compose/Kubernetes templates.
- Add fail-closed production validation.
- Add daily/monthly request, token, and cost budgets plus per-user quotas.
- Redact secrets in admin configuration views.

### Acceptance Criteria

- Each task resolves to one explicit provider/model/policy before execution.
- Cross-provider fallback occurs only when configured and is recorded in the run.
- Budget exhaustion stops new paid calls while deterministic extraction continues.
- Kubernetes/Compose validation covers every provider configuration without
  persisting rendered secrets.
- Store privacy disclosures detect external AI settings consistently.

### AI Notes

Default recommendation: Ollama for private/local processing; OpenRouter or Hugging
Face as explicitly enabled hosted options; generic OpenAI-compatible as an
operator-managed final option.

---

## AI-010 — Add AI Run Provenance and Audit Data

Status: **Completed — 2026-09-12**

Implementation evidence:

- Migration `012_ai_run_audit.py` adds `ai_runs`, `ai_field_provenance`, and the
  lifecycle-ready `item_embeddings` store with cascade ownership and indexes for
  user, item/version, provider, and status queries.
- The AI run recorder creates a record before every application model invocation
  and completes it with requested/resolved model, task, job/workflow IDs,
  prompt/schema version, SHA-256 content fingerprint, bounded status/error code,
  latency, finish reason, token usage, cost, and captured fallback chain.
- Failed provider attempts and deterministic summaries are separate outcomes;
  deterministic runs use provider `deterministic`, zero attempts, and explicit
  field provenance rather than masquerading as model output.
- Summary, detailed summary, suggested-tag, classification, entity, and key-phrase
  provenance records identify model versus deterministic origin. The embedding
  store is user/item/version/model/hash scoped for the later embedding pipeline.
- Normal audit rows have no raw prompt, raw response, source content, provider
  credential, or endpoint columns. Encrypted debug payload and expiry columns are
  reserved for a future explicitly enabled diagnostic mode and remain unset.
- Added an admin-only, filterable `/api/v1/admin/ai/runs` metadata contract that
  cannot return content or credentials.
- Portable account export now includes AI runs, field provenance, and embeddings.
  Account deletion explicitly removes AI provenance, embeddings, and usage data
  before deleting the user, making behavior deterministic even without FK-cascade
  enforcement.

Validation evidence:

- Backend Ruff and Black checks pass; full backend suite: `123 passed`.
- Recorder tests prove successful calls, normalized failures, deterministic
  fallback, content hashing, token/cost capture, generated-field provenance, and
  absence of source content and credentials from stored rows.
- Admin API contract, portable export, account deletion, and migration
  upgrade/downgrade paths pass, including deletion of run, provenance, and vector
  records.

### Problem

The application cannot tell whether an output came from Ollama, n8n, a fallback,
or a future provider, nor measure latency, cost, quality, or failure patterns.

### Task

Add an `ai_runs` audit model and explicit provenance on generated item fields.

### Description

- Record task, item ID, analysis version, workflow/run ID, provider, requested and
  resolved model, prompt/schema version, content hash, status, timestamps, latency,
  attempts, finish reason, token usage, estimated cost, fallback chain, and
  sanitized error code.
- Do not store raw prompts/responses by default.
- Optionally store encrypted debug payloads only under an expiring, audited
  diagnostic mode.
- Track field-level provenance for summary, suggested tags, classification,
  entities, and embeddings.
- Add retention and deletion behavior aligned with account deletion.

### Acceptance Criteria

- Every model invocation creates one auditable run record.
- Deterministic fallback creates a clearly identified non-model run/outcome.
- Account deletion removes the user’s AI run and embedding data.
- No raw user content or credentials appear in normal audit records.
- Migration, API-contract, export, and deletion tests pass.

### AI Notes

Content hashes allow reproducibility and cache detection without duplicating raw
personal text in operational tables.

## AI-011 — Implement Temporal and Worker Metrics

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added bounded Prometheus counters, gauges, and histograms for dispatch outcomes,
  worker polls/heartbeats, queue depth and oldest age, stuck analysis, stage
  outcomes/duration, schedule-to-start latency, AI latency/errors/fallbacks,
  token usage, cost estimates, and provider circuit state.
- The database worker, Temporal scheduler, and Temporal activity worker expose
  independent metrics endpoints. Idle loops refresh a heartbeat timestamp, so a
  stopped/wedged process is distinguishable from a healthy worker with no work.
- The Temporal Python worker uses the SDK `Runtime` Prometheus exporter for
  poller, workflow-task, activity-task, retry, and schedule-to-start metrics in
  addition to Memoryhive application metrics.
- Self-hosted Temporal enables its Prometheus endpoint. `ops/prometheus.yml`
  scrapes the API, database worker, Temporal SDK, scheduler, Temporal application
  worker, and Temporal Server as separate jobs. The operations guide documents
  all endpoints and the Temporal Cloud substitution point.
- Model metric labels accept only operator-configured model aliases; unknown
  strings collapse to `other`. Every remaining label is a bounded provider,
  task, backend, component, stage, direction, error/outcome, or dispatch reason.
  No item, user, workflow, request, correlation, or content value is a label.
- Migration `013_observability_correlation.py` adds a correlation ID to analysis
  jobs and AI runs. Request middleware context propagates the API request ID into
  dispatch, Temporal input, activity/provider logs, and run persistence, with
  structured job/workflow/provider/stage log fields.
- Metrics ports and the self-hosted Temporal exporter are wired through local,
  production Compose, Kubernetes configuration, and environment templates.
  OpenTelemetry tracing remains intentionally deferred until the new metric
  label/privacy policy has production cardinality evidence.

Validation evidence:

- Backend Ruff and Black checks pass; full backend suite: `126 passed`.
- Metrics tests prove configured-alias normalization, unknown-model collapse,
  content/identifier exclusion, queue depth/age collection, stopped-versus-idle
  heartbeat behavior, and API-request-to-job correlation propagation.
- Temporal activity/workflow and migration replay/upgrade/downgrade tests pass.
- Build generation and validation pass with `30` tests; Prometheus job coverage
  and self-hosted Temporal exporter configuration are asserted.
- All generated Kubernetes environment/profile manifests remain deterministic
  and pass structural validation with the metrics-port configuration.

### Problem

Current Prometheus monitoring sees HTTP traffic but not workflow health, pollers,
queue age, AI latency, or provider failures.

### Task

Instrument the Temporal Server/Cloud integration, Python workers, scheduler, and
AI gateway.

### Description

- Scrape supported Temporal Server metrics for self-hosted deployments.
- Export Python SDK/worker metrics for task execution, poll success, failures,
  retries, schedule-to-start latency, and activity duration.
- Add application gauges/counters for pending count, oldest pending age, stuck
  analyzing count, outcomes by stage, AI provider errors, fallback count, token
  usage, cost estimate, and circuit state.
- Keep labels bounded; never label metrics by item/user/workflow ID.
- Propagate correlation IDs through API, outbox, Temporal workflow, activity,
  provider call, and persistence logs.
- Add OpenTelemetry tracing only after metrics cardinality and privacy rules are
  defined.

### Acceptance Criteria

- Prometheus shows API, dispatcher, Temporal, worker, activity, provider, and queue
  metrics in a Temporal-enabled environment.
- No metric exposes user content or unbounded identifiers.
- A deliberately stopped worker is distinguishable from an idle healthy worker.
- Provider latency, failures, fallbacks, and usage can be compared by provider,
  model allowlist alias, task, and outcome.

### AI Notes

Track configured model aliases rather than arbitrary raw model strings to prevent
metric-cardinality growth.

## AI-012 — Add Dashboards and Actionable Alerts

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added a registry-driven local `observability` profile containing the full
  Temporal application plus pinned Prometheus, Alertmanager, and Grafana services,
  persistent metrics/dashboard volumes, health checks, and deterministic
  provisioning mounts.
- Provisioned five versioned, repository-owned Grafana dashboards: application
  health, Temporal cluster/workflows, analysis pipeline, AI providers/cost, and
  extraction quality. Queries use the bounded metrics introduced by AI-011 and
  each dashboard links to the owned runbook.
- Added 16 Prometheus alerts covering API/Temporal availability, missing database
  and Temporal pollers, backlog, oldest age, stuck analysis, activity failures,
  degraded/fallback spikes, provider authentication/rate limits/circuit state,
  AI budget exhaustion, and API error/latency regressions.
- Every alert declares severity, owning team, user impact, first checks, recovery,
  and a runbook URL. `docs/runbooks/observability.md` provides matching diagnostic
  queries, safe correlation rules, recovery guidance, and drill instructions.
- Prometheus routes alerts to a provisioned Alertmanager. The local receiver is a
  documented operator webhook; production operators replace that receiver with
  the owned paging/chat integration without changing alert rules.
- Added pinned `promtool` and `amtool` CI gates. Synthetic rule fixtures exercise
  backlog and per-provider circuit alerts and validate their complete labels and
  annotations.

Validation evidence:

- Registry generation, Docker Compose configuration, health registry generation,
  dashboard JSON/query validation, alert metadata validation, and the full
  build-project suite pass: `31 tests`.
- Prometheus `v3.14.0` reports `SUCCESS: 16 rules found`; its synthetic rule test
  reports `SUCCESS` for backlog and circuit drills.
- Alertmanager `v0.30.1` `amtool check-config` reports `SUCCESS` with one routed
  receiver.
- The generated observability Compose profile passes `docker compose config
  --quiet`. A live local container boot was not used as evidence because the host
  Docker Desktop daemon returned a storage I/O error; deterministic generation,
  pinned-tool validation, and CI boot configuration remain passing.

### Problem

Metrics without dashboards and alert delivery do not provide usable operations.

### Task

Create versioned Grafana dashboards, alert rules, and runbook links.

### Description

- Add dashboards for application health, Temporal cluster/workflows, analysis
  pipeline, AI providers/cost, and extraction quality.
- Add alerts for missing pollers, growing backlog, oldest pending age, stuck
  analysis, workflow/activity failure rate, Temporal unavailable, provider auth
  failure, rate limiting, circuit open, budget exhaustion, and degraded/fallback
  spikes.
- Provision or document Alertmanager integration and notification ownership.
- Attach runbook URLs and recommended diagnostic queries to every alert.
- Start from official/community Temporal dashboard examples but validate and own
  the production queries.

### Acceptance Criteria

- A local observability profile starts Prometheus and Grafana with provisioned
  dashboards.
- Synthetic failure drills trigger the expected alerts.
- Every alert identifies severity, owner, user impact, first checks, and recovery.
- Dashboard and alert configuration is validated in CI.

### AI Notes

Temporal’s community dashboards are useful baselines but are not guaranteed as
production-ready. Reference: [Temporal dashboards](https://github.com/temporalio/dashboards).

## AI-013 — Build an Admin Analysis Operations Surface

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added the admin-only `GET /admin/analysis/operations` control-plane contract.
  It reports queue depth and oldest age, status/stage distributions, 24-hour
  throughput and success/degraded rates, provider run/latency outcomes, recent
  categorized errors, and up to 50 recent analysis runs.
- Run summaries expose only an item type plus short opaque ID, workflow/job and
  correlation IDs, version, backend, stage, configured model alias, attempts,
  timestamps, status, and bounded error category. Captured titles, URLs, raw
  text, user email, arbitrary provider messages, prompts, responses, and secrets
  are excluded.
- Added a separately loaded Analysis Operations web panel so an unavailable
  operations/provider service does not hide core admin capabilities. It shows
  healthy/degraded/failed state, provider connectivity, AI versus deterministic
  versus no-enrichment provenance, safe errors, Temporal correlation, and the
  configured operator-only Temporal UI link.
- Added explicitly confirmed retry, cancel, and reanalyze controls. Retry and
  reanalyze create a new analysis version; database cancellation settles locally
  and Temporal cancellation signals the workflow. Duplicate submissions return
  the already accepted result rather than enqueueing duplicate work.
- Migration `014_admin_analysis_operations.py` adds immutable, target-specific
  operator action records containing actor, item/job reference, action, outcome,
  idempotency key, correlation ID, and timestamp without content payloads.
- Provider connectivity continues through the admin-only gateway health path and
  sends no captured user content. `TEMPORAL_UI_URL` is wired through development
  and production templates, generated Compose files, and generated Kubernetes
  manifests.

Validation evidence:

- Backend Ruff and Black checks pass; the full backend suite reports `127
  passed`, including non-admin `403`, redaction, explicit confirmation,
  retry/cancel/reanalyze idempotency, and audit attribution.
- Full frontend suite reports `22 passed`; five focused component tests cover
  empty, healthy, degraded, failed, and unavailable operational states. ESLint,
  TypeScript, and the Vite production build pass.
- Build-project generation and its `31` tests pass. All 12 Kubernetes
  environment/profile outputs regenerate deterministically and the deployment
  suite reports `27 passed`.
- Repository knowledge generation check passes.

### Problem

Admins currently see aggregate analysis counts and legacy processing jobs but not
Temporal workflows, AI providers, individual analysis stages, or model health.

### Task

Add an operator-focused Analysis Operations section to the Admin API and web UI.

### Description

- Show queue depth, oldest age, stage/status distribution, throughput, success
  rate, degraded rate, provider latency, and recent errors.
- List analysis runs by item-safe reference, workflow ID, version, stage, provider,
  model alias, status, timestamps, attempts, and sanitized error.
- Provide links to the operator-only Temporal UI when configured.
- Add guarded retry, cancel, and reanalyze actions.
- Add provider connectivity tests that send no user content.
- Show whether output used AI, deterministic fallback, or no enrichment.
- Do not expose provider secrets or raw cross-user content.

### Acceptance Criteria

- An admin can find why an item is pending, degraded, or failed without database
  access.
- An admin can correlate an application analysis run with its Temporal execution.
- Retry/cancel actions are authorized, confirmed, audited, and idempotent.
- Non-admin users receive `403` for all operational endpoints.
- UI tests cover empty, healthy, degraded, failed, and unavailable states.

### AI Notes

Temporal UI remains the detailed event-history tool. Memoryhive Admin should
provide the product-aware overview and safe links, not duplicate Temporal itself.

---

## AI-014 — Implement Structured Enrichment

Status: **Completed — 2026-09-12**

Implementation evidence:

- Extended the shared versioned enrichment contract with content language and a
  single strict JSON schema used by Ollama, OpenRouter, Hugging Face, n8n, and
  OpenAI-compatible adapters. Common output bounds, confidence validation, and
  prompt-injection/grounding instructions apply before provider-specific output
  can enter product state.
- Added provider-independent normalization with taxonomy version 1, canonical
  classifications and aliases, case-insensitive matching to a user's existing
  tags, duplicate removal, detected-language validation, lexical faithfulness
  gates for summaries, and source-support filtering for topics, tags, entities,
  and key phrases. Rejected values produce bounded warning codes.
- Migration `015_structured_enrichment.py` adds one immutable enrichment record
  per item analysis version. Records retain short/detailed summaries, topics,
  suggested tags, classification, entities, key phrases, language, confidence,
  warnings, provider/model/prompt/schema/taxonomy versions, source fingerprint,
  generation time, linked AI run, and per-field provenance.
- Item metadata exposes the current structured result and field provenance. The
  tenant-scoped `GET /items/{item_id}/enrichments` endpoint exposes version
  history without permitting cross-user access. Account export and explicit
  deletion now include/remove structured enrichment records.
- Deterministic summaries remain the fallback when AI is absent, fails, or
  returns an ungrounded summary. A degraded fallback cannot overwrite a valid
  prior summary, and model and deterministic fields receive distinct provenance.
- Added three repository-owned golden fixtures covering factual technical
  content, research claims, taxonomy aliasing, existing-tag canonicalization,
  and rejection of unsupported topics/tags/entities/key phrases.

Validation evidence:

- Backend Ruff and Black checks pass; full backend suite reports `132 passed`.
- Golden fixtures satisfy their declared lexical-faithfulness thresholds and the
  common schema while malformed/unsupported fields are removed.
- Tests prove record/version idempotency, field generation metadata, tenant
  history access, safe preservation of a prior summary, AI audit behavior after
  grounding rejection, account lifecycle handling, and Alembic upgrade/downgrade.

### Problem

Current AI output is mostly an unstructured summary. Suggested tags and
classification are not validated or fully exposed as product behavior.

### Task

Generate a validated, versioned enrichment record for every analyzable item.

### Description

- Produce short summary, optional detailed summary, topics, suggested tags,
  classification, entities, key phrases, content language, confidence, and
  warnings.
- Ground output in extracted source text and reject unsupported claims where
  practical.
- Normalize classifications against a versioned taxonomy.
- Deduplicate and normalize tag suggestions against the user’s existing tags.
- Preserve the deterministic fallback summary when no AI provider is available.
- Add provider-independent output-length and safety rules.

### Acceptance Criteria

- Enrichment validates against the same schema across every provider.
- Hallucinated or malformed fields do not overwrite valid existing data.
- Each field exposes provider/model/prompt provenance and generated time.
- Golden fixtures meet agreed summary faithfulness and schema-validity thresholds.

### AI Notes

Avoid one giant prompt. Use task-specific prompt templates where independent
evaluation or cheaper models provide better control.

## AI-015 — Make AI Suggestions Useful and Reversible

Status: **Completed — 2026-09-12**

Implementation evidence:

- Migration `016_ai_suggestion_feedback.py` adds immutable, user-private feedback
  events tied to the enrichment/prompt/model analysis version and global
  per-user “never suggest” preferences. Generated enrichment rows remain
  unchanged when a user corrects or applies a suggestion.
- Added tenant-scoped suggestion read and batch-decision APIs with client IDs,
  expected item revisions, atomic accept/reject/never/undo actions, and replay
  idempotency. Stale offline decisions return the normal `409` revision conflict.
- Accepted tags are resolved into normal user tags and immediately become
  searchable. Classification acceptance is stored as AI organization metadata
  with provenance and never overwrites a user category.
- AI-owned tag application is explicitly tracked. Undo removes a tag only while
  the original AI feedback event still owns it; any later manual tag save clears
  that ownership, so user-authored tags cannot be removed by suggestion undo.
- Rejections are scoped to the analysis version, while “never suggest” applies to
  subsequent versions. An optional, disabled-by-default confidence threshold can
  auto-apply tags above the configured value, records `auto_accept` provenance,
  honors never-suggest preferences, and never changes categories.
- Web item detail now separates suggestions from user tags and provides accept,
  reject, accept all, never, and undo controls plus classification/topics.
  Library organization filters include generated classification and topics.
- Mobile exposes equivalent review controls. Decisions update the local SQLite
  cache immediately, enter the normal mutation queue, retry after connectivity
  returns, and replay against the current server revision after conflicts.
- Suggestion feedback/preferences are included in user export and explicitly
  erased during account deletion.

Validation evidence:

- Full backend suite reports `134 passed`; Ruff, Black, migration upgrade and
  downgrade, cross-tenant access, batch idempotency, stale revision conflicts,
  undo, reanalysis, never-suggest, manual override protection, and threshold
  auto-apply tests pass.
- Web ESLint/TypeScript/Vite checks pass; full suite reports `24 passed`, with
  focused accept-all/reject/never/undo tests that prove model output is not
  mutated.
- Mobile typecheck and Expo lint pass; full suite reports `68 passed`, including
  local decision projection and offline suggestion conflict replay.
- Build generation and `31` tests pass; all Kubernetes outputs regenerate and
  the deployment suite reports `27 passed` with the new threshold configuration.

### Problem

Suggested tags and classification are hidden in metadata and do not reduce manual
organization effort.

### Task

Add web/mobile experiences for reviewing and applying AI suggestions.

### Description

- Display AI-suggested tags separately from user tags.
- Allow accept, reject, accept all, undo, and “never suggest this tag.”
- Optionally auto-apply only above a configurable confidence threshold and preserve
  provenance.
- Show classification/topics in item detail and organization filters.
- Sync suggestion decisions offline and resolve them with normal revision rules.
- Record corrections as feedback without changing historical model output.

### Acceptance Criteria

- Suggestions never silently replace user-authored tags or categories.
- Accepted suggestions become normal searchable tags.
- Rejected suggestions do not immediately reappear for the same analysis version.
- Web and mobile provide equivalent review behavior, including offline decisions.
- Tests cover sync conflicts, undo, reanalysis, and user/manual overrides.

### AI Notes

User corrections are higher-value moat data than raw generated tags. Keep them
private and linked to the prompt/model version that produced the suggestion.

## AI-016 — Add Document Chunking and Embeddings

Status: **Completed — 2026-09-12**

Implementation evidence:

- Migration `017_embedding_indexes.py` adds durable `document_chunks` plus an
  immutable embedding-index registry keyed by provider, model, dimensions,
  normalization, and version. Existing vectors are retained in explicit legacy
  index schemas during upgrade rather than being silently reinterpreted.
- Structured chunking records stable content-derived IDs, ordinals, overlap,
  exact source offsets, hashes, item ownership, and analysis version. The same
  configured boundaries are used by database and Temporal execution.
- The provider-neutral embedding pipeline supports every adapter that explicitly
  declares embedding capability: Ollama, Hugging Face, restricted generic
  OpenAI-compatible endpoints, and OpenRouter only when a separate allowlisted
  embedding model is configured.
- New vectors are L2-normalized by default and written only into the matching
  immutable index. Identical per-user content hashes reuse an existing vector;
  a new analysis version creates bindings without another provider call.
- Changing provider/model/dimension/normalization/version creates a parallel
  index. The `BackfillEmbeddingsWorkflow` pages by a durable cursor, enforces
  batch/rate caps, validates the worker's expected index version, uses existing
  request/token/cost budgets, and exposes progress in Temporal.
- JSON vector arrays are the deployment-validated portable `pgvector`
  equivalent for the current PostgreSQL 15 and SQLite environments. The
  operational runbook records why pgvector is deferred and the staging gates
  required to replace the physical column without changing index identity.
- Item soft-deletion and account deletion explicitly erase chunks and vectors.
  Account export includes chunk offsets/hashes and full embedding index
  provenance.
- Added environment, Compose, and Kubernetes settings for dimensions,
  normalization, index version, chunk boundaries, and backfill limits, plus the
  model-migration and rollback runbook.

Validation evidence:

- Backend Ruff and Black checks pass; the full suite reports `139 passed`,
  including unchanged-chunk reuse, parallel model/dimension indexes, cursor
  resume, Temporal rate limiting, deletion cleanup, chat-only OpenRouter
  rejection, adapter embedding conformance, and Alembic upgrade/downgrade.
- The committed provider-neutral evaluation corpus reports mean Recall@2 above
  `0.95` and enforces a `50 ms` local ranking latency ceiling.
- Build generation reports `31 passed`; all 12 Kubernetes outputs regenerate,
  and deployment validation reports `27 passed` with the embedding configuration
  present in application ConfigMaps and overridable through deployment secrets.
- Operational procedure is documented in `docs/runbooks/embedding-indexes.md`.

### Problem

Keyword search cannot find concepts when the query and saved content use different
words, and large content cannot be retrieved at passage level.

### Task

Add versioned chunks, embeddings, and a provider-neutral embedding pipeline.

### Description

- Add PostgreSQL `pgvector` or an approved equivalent after deployment validation.
- Chunk by content structure with overlap, stable chunk IDs, source offsets, and
  content hashes.
- Record embedding provider, model, dimension, normalization, and version.
- Support Ollama, Hugging Face, and generic OpenAI-compatible embeddings when the
  selected endpoint declares and passes that capability.
- Do not assume OpenRouter chat model availability implies an embedding model.
- Re-embed only changed chunks.
- Add bounded backfill and model-migration workflows.

### Acceptance Criteria

- Identical unchanged chunks are not re-embedded.
- Changing an embedding model or dimension creates a controlled parallel index or
  migration, not silent corruption.
- Account/item deletion removes related chunks and vectors.
- Embedding backfill is resumable, rate-limited, observable, and cost-bounded.
- Retrieval tests measure Recall@K and latency on a committed evaluation corpus.

### AI Notes

Embedding model and dimension are part of the index schema. They must never be
treated as a runtime string that can change without migration.

## AI-017 — Implement Hybrid Search and Optional Reranking

Status: **Completed — 2026-09-12**

Implementation evidence:

- Search now retrieves exact/keyword and semantic passage candidates
  independently after applying owner, source, date, type, category, archive, tag,
  and cursor filters. Semantic vectors are read only from the active immutable
  provider/model/dimension/normalization/version index and current item analysis
  version.
- Deterministic weighted reciprocal-rank fusion combines both lists with
  configuration for candidate count, `k`, keyword/semantic weights, similarity
  threshold, and end-to-end latency budget. Exact title, URL/domain, tag, source,
  and phrase matches receive explicit boosts and stable ID tie-breaking.
- Every search result can include a content-safe `search_match` with bounded
  score, reasons, best passage snippet, and semantic score. The web card renders
  this explanation; the mobile contract accepts it while mobile continues to
  provide its existing provider-independent on-device keyword search offline.
- Query content/vectors are never persisted. Query embeddings use the same
  privacy routing, provider capability checks, circuit/retry policy, immutable
  index schema, usage accounting, quotas, and request/token/cost budgets as
  document embeddings.
- Added the provider-neutral reranking contract and gateway validation. Ollama
  implements a temperature-zero, JSON-schema-constrained reranker. The optional
  reranking pipeline caps candidate text/count, enforces a separate latency
  budget, records usage/cost, rejects unknown/duplicate IDs, and leaves the
  deterministic order unchanged on timeout, budget exhaustion, or provider
  failure.
- With hybrid search disabled, no embedding route, an offline provider, no
  matching index, or a latency failure, the API returns keyword results without
  failing capture/search. Added bounded search mode/outcome and latency metrics,
  a Grafana p95 panel, a 750 ms alert, and recovery instructions.
- Added complete environment, Compose, and Kubernetes tuning surfaces for hybrid
  ranking and reranking limits.

Validation evidence:

- Backend Ruff and Black checks pass; the full backend suite reports `143
  passed`. Tests prove exact and semantic fusion, filters-before-ranking,
  cross-tenant isolation, snippets/reasons, AI-disabled keyword behavior,
  active-index/version checks, bounded/cost-recorded reranking, and malformed
  reranker rejection.
- The committed retrieval corpus measures Recall@2 and NDCG@2 above `0.95`, both
  above its synonym-miss keyword baseline, with the local ranking latency ceiling
  below `50 ms`.
- Web lint/build and `25` tests pass, including explanation/snippet rendering;
  mobile typecheck/lint and `68` tests pass, including offline local search.
- Build generation and `31` tests pass. Deployment rules/config validation
  reports `26 passed`; the environment-sensitive kubectl dry-run initially timed
  out and then passed independently (`1 passed`) across all 12 manifests.

### Problem

Vector-only search can miss exact identifiers, while keyword-only search misses
semantic matches.

### Task

Combine existing PostgreSQL full-text search with vector similarity and optional
reranking.

### Description

- Retrieve keyword and semantic candidates independently.
- Fuse rankings with a deterministic, tunable method.
- Preserve exact title, URL, domain, tag, and phrase-match boosts.
- Support source, date, type, category, archive, and tag filters before final
  ranking.
- Return matched passage snippets and an explanation such as exact, semantic, tag,
  source, or recency match.
- Add an optional reranker capability with strict latency and cost budgets.
- Retain keyword-only behavior when embeddings are unavailable or offline.

### Acceptance Criteria

- Search remains functional with every AI provider disabled.
- Hybrid retrieval improves agreed Recall@K/NDCG metrics over the keyword baseline.
- Exact-match regression tests do not degrade.
- Search p95 meets the agreed web and mobile latency budget.
- Results explain why they matched without exposing hidden prompts or other users’
  data.

### AI Notes

Hybrid retrieval, evaluation, and user-specific ranking signals create more
durable differentiation than a generic summary endpoint.

## AI-018 — Add Related Memories, Duplicate Detection, and Resurfacing

Status: **Completed — 2026-09-12**

Implementation evidence:

- Migration `018_item_interactions.py` adds private, append-only interaction
  events for resurfacing exposure, dismiss, pin, useful, and undo actions, with
  tenant/client idempotency and explicit reversal links. Events contain bounded
  reason/score metadata rather than item content.
- Added owner-scoped related-memory and duplicate-candidate APIs. Related ranking
  combines current-index passage similarity, normalized tags, topics, entities,
  key phrases, and source/domain signals with deterministic tie-breaking and a
  human-readable reason for every result.
- Duplicate detection identifies normalized URL, normalized text/upload hash,
  and high semantic-similarity candidates. It only returns suggestions: no API or
  UI path merges, overwrites, or deletes either item.
- Added a deterministic resurfacing feed using memory age, favorite state,
  prior useful/pin/dismiss feedback, interest overlap, exposure history, and
  configurable per-source/per-topic diversity. Frequency windows, exposure caps,
  and minimum intervals prevent repetition; pinned items remain deliberately
  recoverable.
- Dismiss/pin/useful feedback is idempotent and immediately changes future
  ranking. Undo is an immutable reversal, rejects foreign/already-reversed events,
  and restores the prior deterministic behavior.
- Web item detail displays duplicate warnings and related-memory explanations;
  its library “Rediscover” panel provides useful, pin, dismiss, and undo controls.
  Mobile computes exact duplicates and tag/source relationships from synchronized
  local data, explicitly documenting that nothing is automatically merged and
  remaining useful offline.
- Interaction history is included in account export and explicitly erased for
  item/account deletion. All thresholds, limits, frequency controls, Compose,
  and Kubernetes settings are configurable.

Validation evidence:

- Backend Ruff and Black checks pass; the full suite reports `145 passed`,
  including migration round-trip, exact/near duplicate classes, current-index
  semantic scoring, cross-tenant exclusion, source/topic diversity, immediate
  exposure suppression, client idempotency, dismiss/undo behavior, and item
  interaction cleanup.
- Web lint/build and `26` tests pass, including explicit duplicate-no-merge and
  related-reason rendering. Mobile typecheck/lint and `69` tests pass, including
  provider-free offline duplicate/connection ranking.
- Build generation and `31` tests pass; all 12 Kubernetes outputs regenerate and
  deployment/configuration validation reports `27 passed`.

### Problem

Memoryhive stores content but does not yet connect or proactively recall it in a
meaningful, explainable way.

### Task

Use embeddings, entities, tags, source, time, and user interaction signals to add
related-item and resurfacing features.

### Description

- Detect exact and near duplicates during/after capture.
- Show related memories on item detail with a match explanation.
- Build an explainable resurfacing feed using relevance, recency, diversity, and
  prior interaction—not arbitrary model generation.
- Let users dismiss, pin, or mark suggestions useful.
- Add frequency caps and avoid repeatedly resurfacing rejected items.
- Keep recommendations user-scoped and available from synchronized local data
  where practical.

### Acceptance Criteria

- Duplicate suggestions never merge or delete data without confirmation.
- Related results are owner-scoped and meet offline/online behavior documented in
  the UI.
- Every resurfaced item has a human-readable reason.
- User feedback changes future ranking behavior deterministically and reversibly.
- Diversity prevents one source/topic from dominating the feed.

### AI Notes

This is a primary AI-moat feature: the value comes from a user’s accumulated
private memory graph and feedback, not from access to a commodity model.

## AI-019 — Add Grounded Recall Answers as a Controlled Follow-up Feature

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added a provider-neutral, single-turn grounded-recall pipeline. It sends only
  bounded owner-scoped retrieved passages through the existing explicit provider
  policy and database-backed per-user/system budget guard; it never performs web
  search or accepts conversational history.
- Each generated factual sentence must pass a server-side lexical grounding check
  against a retrieved passage. Supported claims receive structured citation IDs;
  any unsupported claim converts the entire response to an explicit
  insufficient-evidence result rather than being shown as an answer.
- Added `POST /items/recall` with saved-item/passage citations, provider/model and
  latency provenance, tenant-scoped retrieval, and safe unavailable behavior.
  A web “Ask your memories” surface links every citation to its accessible item.
- Backend and independently compiled web flags default off. Backend enablement
  additionally requires `AI_EVALUATION_RELEASE_GATE_PASSED=true`; configuration
  validation rejects recall enablement without that gate. Provider routing,
  fallback, payload bounds, and answer bounds are configurable across Compose and
  Kubernetes.

Validation evidence:

- Backend Ruff/Black and the full suite pass with `148 passed`, including feature
  gating, unsupported-claim refusal, working citations, and cross-user passage
  exclusion.
- Web lint/build and `27` tests pass, including a saved-item citation navigation
  test. Runtime generation and `31` build tests pass; all Kubernetes variants
  regenerate and deployment validation reports `27 passed`.
- AI-020's versioned offline release evaluation passes groundedness and citation
  correctness at `1.0`, p95 latency at `310 ms`, estimated cost at `$0.00`, and
  all retrieval floors. Runtime rollout remains independently disabled by default
  and requires an operator to set both the feature flag and accepted-gate flag.

### Problem

Users may eventually need synthesis across saved material, but ungrounded “chat
with notes” would violate trust and was an explicit v1 non-goal.

### Task

Design and implement grounded recall answers only after hybrid retrieval and
evaluation meet their release gates.

### Description

- Answer only from owner-scoped retrieved passages.
- Cite each answer claim to saved items and matched passages.
- Provide “insufficient evidence” behavior.
- Keep the initial interaction single-turn or tightly bounded.
- Do not use web search unless introduced later as a separate, explicit feature.
- Enforce provider/privacy policy and per-user budgets.

### Acceptance Criteria

- Every substantive answer contains working citations to accessible saved items.
- The system refuses or qualifies answers not supported by retrieved material.
- Cross-user leakage tests pass.
- Groundedness, citation correctness, latency, and cost meet defined evaluation
  thresholds.
- This feature remains disabled until AI-016, AI-017, and AI-020 are accepted.

### AI Notes

This is deliberately not the first AI feature. Reliable retrieval and provenance
must precede generative answers.

---

## AI-020 — Create the AI Evaluation System

Status: **Completed — 2026-09-12**

Implementation evidence:

- Added a versioned `memoryhive-ai-v1` corpus explicitly marked as synthetic and
  public-domain, with no production user data. It covers link, screenshot, text,
  English/Hindi OCR, extraction, schema validity, summaries, tags, topics,
  classification, entities, key phrases, semantic queries, related results, and
  supported/unsupported grounded answers.
- Added deterministic extraction accuracy, token F1, precision/recall/F1,
  classification, Recall@K, MRR, NDCG, related Recall@K, groundedness, citation
  correctness, p95 latency, fallback-rate, and estimated-cost measurements.
- Versioned release floors and a provider/model/prompt/schema/dataset-qualified
  baseline produce blocking failures and separate non-blocking trend warnings.
  A regression test proves quality drops fail rollout.
- Normal CI runs without provider credentials, writes a redacted comparable JSON
  report, and uploads it as an artifact. Existing deterministic provider-contract
  suites exercise OpenRouter, Hugging Face, Ollama, n8n, and OpenAI-compatible
  behavior without paid calls.
- Added a separate scheduled/manual live-evaluation workflow. It is skipped unless
  explicitly enabled, sends only a fixed synthetic prompt, stores no response
  content, uses secret-backed provider configuration, and enforces a hard maximum
  estimated-cost cap of USD 0.05.
- `evaluations/README.md` documents corpus governance, execution, baseline update
  review, privacy constraints, and opt-in live-provider operation.

Validation evidence:

- Backend Ruff/Black and the full suite pass with `153 passed`, including corpus
  governance, deterministic baseline comparison, blocking regression detection,
  live opt-in/cost-cap enforcement, and all AI provider contract suites.
- The release evaluator exits successfully with no blocking failures: all quality
  metrics are `1.0`, p95 latency is `310 ms`, fallback rate is `0.0`, and estimated
  cost is `$0.00`, satisfying every versioned floor and closing AI-019's dependency.

### Problem

There is no objective way to compare models, prompts, extraction quality, search
quality, or releases.

### Task

Create offline and integration evaluations with versioned datasets and thresholds.

### Description

- Build consent-safe fixtures for links, screenshots, multilingual OCR, notes,
  summaries, tags, classification, entities, semantic queries, related items, and
  grounded answers.
- Measure extraction accuracy, OCR quality, schema validity, summary faithfulness,
  tag precision/recall, classification accuracy, Recall@K, MRR/NDCG, groundedness,
  latency, fallback rate, and estimated cost.
- Add provider contract tests that do not require paid credentials in normal CI.
- Add opt-in nightly/live evaluations for configured providers.
- Store evaluation results by provider, model, prompt, schema, and dataset version.
- Define release-blocking floors and non-blocking trend warnings.

### Acceptance Criteria

- CI runs deterministic offline evaluations with no external provider keys.
- Live provider evaluations are opt-in, budget-capped, and redact user content.
- A prompt/model change produces a comparable report against the current baseline.
- Quality regressions beyond agreed thresholds block rollout.
- Evaluation datasets contain no unapproved production user data.

### AI Notes

The evaluation corpus and correction signals are strategic assets. Version them
carefully and separate synthetic/public fixtures from consented private examples.

## AI-021 — Complete End-to-End and Failure Testing

Status: **Completed — 2026-09-12**

Implementation evidence:

- `--temporal` is now an asserting acceptance mode, not a profile alias. It runs
  the offline AI release evaluation, captures synthetic text/link/screenshot
  items through the running API, waits for terminal analysis state, connects to
  the real Temporal service, and verifies each deterministic workflow ID has
  persisted history.
- The same command runs deterministic Temporal and provider-stub suites covering
  ordered stages, replay, cancellation, stale versions, duplicate dispatch,
  worker absence/recovery, transient provider failure/retry, timeout/rate limit,
  malformed output, exhaustion, circuit breaking, fallback, and provider policy.
- Added a bounded live-stack load gate that concurrently captures 20 items,
  observes and waits for the analysis backlog to drain, then measures ten search
  requests against a configurable 2-second p95 ceiling.
- Acceptance artifacts contain workflow IDs, item types, terminal states, history
  event counts, content-safe metrics, evaluation results, burst/backlog/search
  measurements, and no credentials or saved content. Failures additionally
  collect a bounded Compose log tail with token/key/password/Bearer redaction.
- Added desktop and mobile Playwright flows for AI suggestions with undo,
  provider/model provenance, semantic match explanations, and degraded provider
  state. Existing component/API tests cover analysis operations and retry paths.
- CI now separates fast credential-free backend tests, a real Docker Temporal
  integration lane, and the separately opt-in live-provider evaluation workflow.

Validation evidence:

- Backend Ruff/Black and all `155` tests pass. The Temporal-focused suite reports
  `6 passed`, including retry after a synthetic provider timeout and successful
  execution after the workflow was durably queued with no worker available.
- Web lint/build and `27` unit tests pass; the expanded Playwright suite reports
  `4 passed` across desktop and mobile.
- The automation script passes Node syntax validation, and a `--temporal --dry-run`
  proves the canonical sequence includes real workflow-history acceptance,
  deterministic failure suites, evaluation output, and the bounded load gate.
  The local Docker daemon was unresponsive, so the real-container execution is
  assigned to the new isolated CI lane and was not claimed as a local run.

### Problem

Starting a Temporal profile does not prove workflows execute, retry, persist, and
surface correctly.

### Task

Add real Temporal, provider-stub, web, mobile, and operational integration tests.

### Description

- Add a Temporal test environment or container-backed suite.
- Capture each item type and wait for the expected workflow and terminal state.
- Test worker termination, Temporal interruption, provider timeout/rate limit,
  malformed output, retry exhaustion, circuit breaker, fallback, cancellation,
  stale version, and duplicate dispatch.
- Extend automation so `--temporal` asserts Temporal behavior rather than only
  starting the profile.
- Add browser tests for AI provenance, suggestions, analysis operations, semantic
  search, and degraded states.
- Add load tests for capture bursts, analysis backlog, and search latency.

### Acceptance Criteria

- One documented command runs the complete local Temporal-backed acceptance suite.
- Tests prove recovery after worker and provider failures.
- No test depends on a paid external model by default.
- Test artifacts include workflow IDs, sanitized logs, metrics snapshots, and
  evaluation results when a scenario fails.
- CI clearly separates fast unit tests, container integration tests, and opt-in
  external-provider tests.

### AI Notes

Use deterministic provider stubs for schema and failure testing. Live-model tests
measure behavior but must not be the sole correctness gate.

## AI-022 — Enforce Privacy, Security, and Data Governance

Status: **Completed — 2026-09-12**

Implementation evidence:

- External AI processing is user opt-in and defaults off. Web and mobile settings
  explain the transfer boundary; the authenticated API, account export, and
  migration persist the preference.
- Provider routes carry local/self-hosted/third-party classification. Dispatch,
  Temporal activities, the database worker, direct analysis, embeddings,
  reranking, and grounded recall enforce both operator policy and current user
  consent. Workers re-check consent at execution, so opting out after queueing
  removes an external primary and promotes only an allowed local fallback.
- `docs/AI_DATA_GOVERNANCE.md` now owns the provider register, data-flow diagram,
  minimized payload rules, retention/deletion/residency/logging policy, threat
  controls, and incident responsibilities. The public privacy policy and mobile
  store data-safety/submission material match the implemented behavior.
- Provider credentials remain server-side secret references and are redacted
  from deployment artifacts, APIs, logs, and test artifacts. Generic compatible
  endpoints enforce exact host allowlists, DNS/literal private-address checks,
  redirect denial, sensitive-header blocking, and payload ceilings.
- Account deletion explicitly removes chunks, embeddings, enrichment records,
  AI runs/usage, interactions, suggestions, feedback, and preferences; export is
  owner scoped and includes the AI privacy setting and derived records.

Validation evidence:

- Backend Ruff/Black and all `158` tests pass, including local-only routing,
  queued opt-out, SSRF/redirect/header injection, secret redaction, oversized
  input, tenant isolation, account export/deletion, and migration round-trip.
- Web lint/build and `27` tests pass. Mobile typecheck/lint and `69` tests pass;
  the store submission packet is current and the automated privacy consistency
  check reports no repository blocker. Its remaining 12 release blockers are
  pre-existing real signing, store-console, reviewer-account, and operator-contact
  evidence—not privacy implementation failures.

### Problem

External AI connectivity sends private captured content outside Memoryhive’s
deployment and changes privacy, retention, and mobile-store disclosures.

### Task

Implement explicit AI privacy controls and update all operational and release
documentation.

### Description

- Classify providers as local, self-hosted, or third-party.
- Add an operator policy and user-facing disclosure for external processing.
- Consider a user opt-out before enabling third-party processing in production.
- Minimize provider payloads and strip unnecessary metadata.
- Define retention, deletion, residency, and diagnostic logging rules.
- Encrypt provider credentials in the deployment secret manager; never store them
  in repository files or return them through APIs.
- Apply SSRF and redirect protections to generic provider endpoints.
- Update privacy policy, data-safety declarations, threat model, account export,
  and deletion verification.

### Acceptance Criteria

- A user or deployment configured for local-only processing makes no third-party
  AI calls.
- External provider enablement is reflected by automated store/privacy checks.
- Security tests cover SSRF, redirects, header injection, secret redaction,
  oversized inputs, cross-user access, and deletion.
- Account deletion removes embeddings, suggestions, feedback, and AI audit data.
- A data-flow diagram and provider register identify every external transfer.

### AI Notes

Private/local intelligence can be part of the moat. Privacy should be represented
as a product capability, not only a legal disclosure.

## AI-023 — Rollout, Migration, and Production Readiness

Status: **Completed — 2026-09-12**

Implementation evidence:

- Temporal, Ollama, n8n, OpenRouter, Hugging Face, OpenAI-compatible,
  enrichment, embeddings, shadow/hybrid ranking, suggestions, related items,
  resurfacing, grounded recall, and embedding backfill now have independent
  server/deployment flags. Disabling a provider filters configured routes rather
  than preventing startup, so deterministic capture and keyword search continue.
- Hybrid search has a real shadow mode: it executes and measures candidate
  ranking, records top-k overlap, and returns the unchanged keyword control order.
  Production manifests default to shadow on and user-visible hybrid ordering off.
- Embedding backfill is independently disabled by default, cursor-resumable,
  rate/batch/budget bounded, sequential within its configured concurrency ceiling,
  and accepts Temporal pause/resume signals. Rollback retains the old immutable
  embedding index and never removes source content.
- `ops/ai-rollout-policy.json` is the machine-readable flag baseline, ownership,
  staging-gate, SLO, backfill, and capacity/cost contract. CI runs
  `scripts/validate_ai_rollout.py`; an optional evidence record fails closed until
  every staging artifact passes and a named owner records an explicit go decision.
- `docs/AI_PRODUCTION_READINESS.md` defines rollout order, immediate provider and
  Temporal rollback, capacity forecasts at 10k/100k/1m monthly items, on-call
  ownership, failure drills, and the go/no-go checklist. The observability runbook,
  dashboards, alerts, environment examples, Compose generation, Kubernetes
  generation, and Knowledge catalog now reference the same controls.

Validation evidence:

- Backend Ruff/Black and all `161` tests pass, including independent provider and
  feature rollback, unchanged source content, shadow ranking, bounded backfill,
  and provider-concurrency validation. The final offline evaluation passes every
  blocking quality and operational threshold.
- All six generated Compose configurations pass `docker compose config --quiet`.
  Build generation is deterministic and all `31` build tests pass. All 12
  Kubernetes local/staging/production × infra/app-only/full/temporal combinations
  pass client-side kubectl dry-run validation; deployment deterministic-render
  coverage passes.
- The rollout policy and dashboard JSON validate, Knowledge generation is current,
  and alert/rule YAML parses. Promtool/Alertmanager container validation remains
  enforced in CI because the local Docker daemon was unavailable for container
  execution during this run.
- Web lint/build and `27` tests and mobile typecheck/lint plus `69` tests remain
  green from AI-022. Automated store/privacy consistency has zero repository
  blockers; real signing/store-console evidence remains a release gate.

Production enablement note: implementation is complete, but the checked-in
example release evidence intentionally says **no-go**. A real staging environment
must supply and approve the required failure-drill, load, backup/restore, privacy,
store, dashboard, and shadow-quality artifacts before any production flag change.

### Problem

A large AI/Temporal change needs reversible rollout, cost controls, migration
proof, and operating ownership.

### Task

Ship the work through staged feature flags and production-readiness gates.

### Description

- Add feature flags for Temporal dispatch, each provider, structured enrichment,
  embeddings, hybrid search, suggestions, related items, resurfacing, and grounded
  answers.
- Run shadow evaluation before changing user-visible search ranking.
- Backfill in bounded cohorts with pause and rollback controls.
- Define SLOs for capture availability, analysis completion, queue age, search
  latency, enrichment quality, degraded rate, and cost per analyzed item.
- Create capacity and cost forecasts for expected item volume.
- Add on-call ownership, incident runbooks, rollback steps, and provider-disable
  switches.
- Validate Compose and all Kubernetes environment/profile combinations.
- Update Knowledge files and requirements traceability after implementation.

### Acceptance Criteria

- Features can be enabled independently by environment and rolled back without
  deleting source content.
- A provider can be disabled immediately while deterministic capture/search remain
  operational.
- Backfill respects configured concurrency and budget limits.
- Staging completes failure drills, load tests, backup/restore verification, and
  privacy review before production enablement.
- Production rollout has named owners, dashboards, alerts, runbooks, and an
  approved go/no-go checklist.

### AI Notes

Do not equate provider connectivity with feature readiness. User-visible rollout
requires provenance, evaluation, monitoring, privacy, and graceful degradation.

---

## Proposed Configuration Surface

Names are illustrative and should be finalized during AI-004/AI-009 design.

```text
AI_ENABLED=false
AI_DEFAULT_PROVIDER=ollama
AI_ALLOWED_PROVIDER_CLASSES=["local"]
AI_FALLBACK_ENABLED=false
AI_STORE_DEBUG_PAYLOADS=false

AI_SUMMARY_PROVIDER=ollama
AI_SUMMARY_MODEL=qwen2.5:3b
AI_ENRICHMENT_PROVIDER=openrouter
AI_ENRICHMENT_MODEL=<allowlisted-model-alias>
AI_EMBEDDING_PROVIDER=huggingface
AI_EMBEDDING_MODEL=<pinned-model-and-revision>
AI_RERANK_PROVIDER=
AI_RERANK_MODEL=

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=https://www.memoryhive.in
OPENROUTER_APP_NAME=Memoryhive

HF_TOKEN=
HF_INFERENCE_BASE_URL=https://router.huggingface.co/v1

OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=
OPENAI_COMPATIBLE_CAPABILITIES=["chat"]
OPENAI_COMPATIBLE_ALLOWED_HOSTS=[]
```

Requirements:

- secrets remain environment/secret-manager values;
- public clients never receive provider credentials;
- base URLs are normalized and validated;
- model aliases map to operator-approved concrete models;
- changing an embedding model requires an index migration;
- production startup fails closed for unsafe provider configuration.

## Proposed Data Additions

- `analysis_outbox`: transactional scheduling intent and delivery audit.
- `ai_runs`: provider/model/prompt/schema/usage/cost/outcome provenance.
- `item_enrichments`: versioned structured enrichment and field provenance.
- `item_chunks`: source offsets, hashes, normalized chunk text, and version.
- `item_embeddings`: vector, model revision, dimensions, and chunk relationship.
- `ai_suggestion_feedback`: accepted/rejected/undone suggestions and reason.
- `item_interactions`: privacy-scoped retrieval/resurfacing signals.
- Additional item analysis timestamps/stages required by the revised state machine.

Exact normalization may combine tables where justified, but raw prompts and
responses must not be stored by default.

## Definition of Done

AI Goal 1 is complete only when:

- all P0 lifecycle defects are fixed in Temporal and non-Temporal modes;
- OpenRouter and Hugging Face connectivity pass shared conformance and live opt-in
  tests;
- the generic OpenAI-compatible adapter works with approved OpenAI-compatible and
  DeepSeek fixtures and at least one staging endpoint;
- provider use is explicit, observable, budgeted, and privacy-controlled;
- Temporal and AI metrics, dashboards, alerts, runbooks, and Admin operations are
  working;
- structured enrichment and suggestion review work on web and mobile;
- hybrid retrieval demonstrates measurable improvement over keyword search;
- related/resurfacing behavior is explainable and feedback-aware;
- deterministic offline capture and keyword search remain operational with every
  AI provider disabled;
- migrations, account export/deletion, backups, and restores include all new data;
- backend, frontend, mobile, automation, Compose, Kubernetes, security, load, and
  evaluation gates pass;
- privacy and mobile-store disclosures match the actual configured data flow;
- implementation results and architectural decisions are recorded in the Goal 1
  documentation and generated Knowledge files are current.

## Production Decisions Still Required

The implementation is safe-by-default. Production flags remain off until owners
confirm:

1. Whether production’s default policy is local-only, hosted opt-in, or hosted by
   default with user opt-out.
2. Whether Temporal Cloud or a self-hosted Temporal cluster will be used in
   production.
3. Whether `pgvector` is approved for the production PostgreSQL deployment.
4. Initial approved model aliases for summary, enrichment, embeddings, and
   optional reranking.
5. Per-user and deployment-wide cost budgets.
6. Whether AI suggestions may ever auto-apply, and at what confidence threshold.
7. Whether grounded recall answers remain outside Goal 1 delivery or are included
   behind a disabled feature flag.
8. Whether encrypted, expiring AI debug payload capture is permitted in staging.

Until these decisions and the staging evidence record are approved, production
AI/Temporal flags must remain at the checked-in no-go baseline.
