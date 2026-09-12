# AI and Temporal Production Readiness

Updated: 2026-09-12

The machine-checked rollout contract is `ops/ai-rollout-policy.json`. Production
starts from its baseline and advances one independently reversible flag at a
time. Disabling any AI provider or feature never deletes source items, extracted
text, the keyword index, prior enrichment versions, or prior immutable embedding
indexes.

## Rollout sequence

1. Deploy migrations and code with external providers, backfill, resurfacing,
   grounded recall, and user-visible hybrid ranking disabled.
2. Exercise deterministic capture and keyword search with every provider off.
3. Enable Temporal and local Ollama separately; verify queue and analysis SLOs.
4. Enable embeddings plus `AI_SEARCH_SHADOW_ENABLED`. Shadow hybrid results are
   measured by top-k overlap but keyword ordering is returned to users.
5. Pass the versioned offline evaluation and review shadow quality/latency. Only
   then enable `AI_HYBRID_SEARCH_ENABLED` for a bounded cohort.
6. Enable suggestions, related items, resurfacing, and grounded recall
   independently. Grounded recall additionally requires the evaluation release
   gate.
7. Enable one external provider only after operator policy, user consent,
   provider register, budget, privacy, and store-disclosure gates pass.

Rollback is the reverse flag change. For provider incidents, first set its
provider flag to false, remove it from all routes/fallbacks, restart API and
workers, then confirm provider-call rate is zero. Deterministic extraction and
keyword search remain available. For Temporal incidents, set `TEMPORAL_ENABLED`
false so new jobs use the database worker; recover already scheduled workflows
from Temporal history rather than editing their state manually.

## Backfill control

Embedding indexes are immutable and coexist by version. Backfill starts only
with `AI_EMBEDDING_BACKFILL_ENABLED=true`, is cursor-resumable, processes bounded
pages sequentially (therefore never exceeding the configured concurrency), obeys
the items/minute limit, and reserves the normal provider/user cost budgets. The
Temporal workflow accepts `pause` and `resume` signals. Disable the flag or
cancel the workflow to stop; retain the previous index and restore its route to
roll back. Never delete the old index until the new index has passed evaluation,
backup/restore, and rollback drills.

## SLOs, dashboards, and alerts

The initial objectives are capture availability 99.9%, 99% analysis completion
within five minutes, oldest queue age below 300 seconds, search p95 below 750 ms,
structured-enrichment schema success at least 98%, provider degraded rate below
2%, and average provider cost at or below $0.02 per analyzed item. The exact
values are checked into the rollout policy.

Use the application health, Temporal workflows, analysis pipeline, AI
provider/cost, and retrieval Grafana dashboards. Alerts cover API/Temporal
availability, missing workers, backlog/queue age, stuck analysis, provider
failure/auth/circuit/budget, search latency, and cost. `product-engineering` owns
the release decision; `ai-platform-on-call`, `platform-on-call`, and the
`privacy-security-reviewer` own their corresponding gates and incidents.

## Capacity and cost forecast

Forecast at 10k, 100k, and 1m items/month. At the $0.02/item ceiling, maximum
provider spend is $200, $2,000, and $20,000/month respectively. At 1,500 average
tokens/item, token demand is 15m, 150m, and 1.5b tokens/month. Storage planning at
12 KiB of AI-derived chunk/vector metadata per item is approximately 117 MiB,
1.14 GiB, and 11.4 GiB before database/index overhead. Worker count is
`ceil(peak items/minute / 30)` and must also remain below provider and database
connection limits. Replace estimates with measured staging usage before go-live.

## Required staging record and go/no-go

The release owner must link artifacts for all of the following and record an
explicit approval: offline evaluation, shadow-ranking review, worker failure
drill, provider timeout/rate-limit/circuit drill, capture-burst/load test,
isolated backup/restore verification, privacy review, and automated store
disclosure check. Also attach the rendered Compose and every Kubernetes
environment/profile validation, dashboard screenshots, alert test output,
current capacity/cost forecast, rollback rehearsal, and named on-call handoff.

Copy `ops/ai-release-evidence.example.json` outside the repository's secret/data
boundary, fill it with artifact references and named approvals, then run
`uv run python scripts/validate_ai_rollout.py --evidence <record.json>`. The
example intentionally validates as no-go until every gate says `passed` and the
release owner records a named `go` decision.

Go only when every artifact passes and no quality, privacy, budget, SLO, or
migration exception is open. A failed gate is a no-go: leave its feature flag
off, preserve source content, and rerun the complete gate after remediation.
