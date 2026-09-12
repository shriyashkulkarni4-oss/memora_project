# Memoryhive AI evaluations

`datasets/memoryhive_ai_v1.json` is a versioned, synthetic/public-domain corpus.
It contains no production user content and covers links, screenshots, text notes,
multilingual OCR, extraction, summaries, tags, topics, entities, key phrases,
classification, semantic retrieval, related memories, grounded answers, latency,
fallback, and estimated cost.

Run the release-blocking offline suite without provider credentials:

```bash
uv run python scripts/run_ai_evaluations.py
```

The command compares provider/model/prompt/schema/dataset-qualified results with
`baseline.json`, applies `thresholds.json`, exits non-zero on a blocking floor,
and writes a redacted report under `evaluation-results/`. A relative regression
that remains above a release floor is reported as a non-blocking trend warning.

Live tests are explicitly opt-in and use only the synthetic probe string:

```bash
AI_LIVE_EVALUATIONS=true uv run python scripts/run_ai_evaluations.py \
  --live-provider openrouter --live-model allowlisted/model --max-live-cost-usd 0.05
```

The provider must already be configured through the normal secret-backed
Memoryhive settings. Live output never stores the prompt or model response, the
cost cap cannot exceed USD 0.05, and CI does not run live calls. The scheduled
workflow is skipped unless the repository variable `AI_LIVE_EVALUATIONS` is
exactly `true`.

When changing a prompt, model, schema, or dataset, change its version first, run
the evaluator, review metric deltas, and update the baseline only through an
explicit reviewed change. Never copy user captures into this directory without
documented consent and a separate private-data handling process.
