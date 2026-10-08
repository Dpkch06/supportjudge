# Measurement report

Run `c191bff6cdd247aaa4bfe94a82747bfa`, recorded 2026-10-07T22:03:15.689016+00:00. Split: heldout. Configuration: `measurement-v1`.

## Scope

30 questions, two live generators, two live judges, and both answer orders. Settings were frozen from Experiment 5 before this run. No rubric tuning used these results.

## Operational results

| Measure | Result |
| --- | --- |
| Submission requests / concurrency / errors | 100 / 5 / 0 |
| Submission p50 / p95 / p99 | 0.0319 / 0.0486 / 0.0517 seconds |
| Completed model calls / cache hits | 300 / 0 |
| Evaluation duration | 978.80 seconds |
| Throughput | 1.839 questions/minute |
| Model-call p50 / p95 / p99 | {'p50': 3.0196, 'p95': 6.0849, 'p99': 7.1947} seconds |
| Per-question provider-time p50 / p95 / p99 | {'p50': 32.2222, 'p95': 40.5565, 'p99': 42.575} seconds |
| Queue wait | Not instrumented |
| Tokens | 260412 |
| Recorded cost / cost per question | $0.011441 / $0.000381 |

Submission timing uses a separate loopback HTTP server with the real validation and SQLite persistence, five concurrent clients and its worker disabled. It excludes model execution. The live run uses the normal single-worker app. Per-question time sums its sequential provider calls and excludes local processing. Queue wait was not instrumented; saved timestamps cannot separate it reliably from report aggregation.

## Model breakdown

| Model | Calls | Tokens | Recorded USD | Latency p50 / p95 / p99 seconds |
| --- | --- | --- | --- | --- |
| anthropic/claude-haiku-4.5 | 120 | 128398 | 0 | {'p50': 2.93, 'p95': 3.6262, 'p99': 3.7752} |
| google/gemini-2.5-flash | 30 | 8704 | 0 | {'p50': 1.3748, 'p95': 1.7854, 'p99': 1.8132} |
| mistralai/mistral-small-3.2-24b-instruct | 120 | 113668 | 0.011441413750000002 | {'p50': 4.0825, 'p95': 6.6596, 'p99': 7.5628} |
| openai/gpt-4.1-mini | 30 | 9642 | 0 | {'p50': 1.9392, 'p95': 3.1168, 'p99': 3.4141} |

## Judge scores

| Judge | Answer | Mean score out of 4 | 95% bootstrap interval | Questions |
| --- | --- | --- | --- | --- |
| anthropic/claude-haiku-4.5 | A | 3.958 | [3.875, 4] | 30 |
| anthropic/claude-haiku-4.5 | B | 3.9 | [3.8417, 3.9583] | 30 |
| mistralai/mistral-small-3.2-24b-instruct | A | 3.983 | [3.9583, 4] | 30 |
| mistralai/mistral-small-3.2-24b-instruct | B | 3.933 | [3.875, 3.975] | 30 |

| Judge | Swapped-order consistency | Mean B minus A | 95% paired interval |
| --- | --- | --- | --- |
| anthropic/claude-haiku-4.5 | 80.0% | -0.0583 | [-0.125, 0.025] |
| mistralai/mistral-small-3.2-24b-instruct | 66.7% | -0.05 | [-0.1, -0.0083] |

## Interpretation and limits

- Submission p95 target of 500 ms: met in this local test.
- Per-question provider-time p95 target of 60 seconds: met. Full end-to-end question latency was not instrumented.
- This completed run has no failed model calls recorded. It is one run, not a long-term reliability estimate. Historical failed experiments are excluded; their partial costs are not fully recoverable from saved reports.
- Bootstrap intervals use 1,000 question-level resamples with seed 42. Related questions share policies; these intervals do not account for policy-family clustering or repeated model sampling.
- Scores and agreement between judges are not human-verified accuracy. Human calibration, false acceptance and false rejection for these generated answers remain unmeasured.
- Model IDs, prompts, rubric, dataset hash and implementation hash are saved in the raw run. Providers control model revisions and sampling defaults, so exact output reproduction is not guaranteed.
- Generator prompts differ as saved in Experiment 5. Results compare answer configurations, not model identity alone.
- Once inspected, this held-out set must not be described as unseen evidence for later tuning.
- API acceptance measurements do not establish sustained load capacity with a busy worker. Cost reflects recorded provider charges or configured estimates, not an account-wide invoice. Some providers returned zero cost for nonzero token usage; these zeros are preserved and may understate actual billing. Per-model zero-cost call counts are included in the JSON.

Raw artifacts: `reports/final-measurements.json`, `reports/heldout-measurement-run.json`, `reports/submission-measurements.json`. Rerun the report with `python infra/report_measurements.py c191bff6cdd247aaa4bfe94a82747bfa`.
