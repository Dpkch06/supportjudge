# First version implementation plan

## Workstream branches

All six branches start from the same planning commit. They are named by responsibility so ownership can change without renaming code.

| Branch | Owner | Scope |
| --- | --- | --- |
| work/domain-evaluation | @Navneet-Scaler | Policy manifest, demo fixtures, scenario schema, annotation guide and human pilot |
| work/judge-engine | @Vijaygaurav2004 | Provider adapters, validated judge output, rubrics, pointwise and swapped pairwise execution |
| work/statistics-ci | @omwagh28 | Scenario bootstrap, agreement metrics, conservative release checks and CI commands |
| work/backend-jobs | @VinnuReddy18 | API, persistence, bounded job queue, team access and append-only review records |
| work/frontend-reports | @VinayakPaka | Experiment form, saved runs, comparison report, evidence inspection and review interaction |
| work/llmops-integration | @Dpkch06 | Packaging, startup, observability, configuration history, tests and integration documentation |

## Build order

1. Agree on input/output records and prepare a labeled-as-synthetic development fixture set. Synthetic cases cannot replace the required team-authored evaluation set.
2. Complete the judge engine and statistics with behavior tests for swapped order, invalid output, missing human labels, and failure paths.
3. Connect persistence and the worker to API submission and reporting. Snapshot all configuration inputs at submission time.
4. Connect the frontend to the same report contract. Inspect the real browser flow and ensure errors remain visible.
5. Add packaging, documented setup, CI smoke checks, report export, trace records and conservative configuration approval.
6. Integrate reviewed workstreams, run the demo end to end, and publish the first-version completion checklist.

## Initial integration decision

Use Python FastAPI, a static browser interface, and SQLite in a single local application for v1. This replaces the proposed Next.js and PostgreSQL stack to reduce setup work before proving evaluation quality. Keep API contracts separate from the interface so those components can migrate later.

Use one application process and one worker thread. Pending jobs are durable. Interrupted running jobs fail explicitly instead of silently repeating paid calls. Bound the queue. Do not deploy multiple application workers with this design.

## Completion evidence

- A clean install can launch the app and run a fixture evaluation without provider keys.
- Demo runs explicitly identify deterministic simulators, never claim human calibration, and never approve releases.
- A configured OpenAI-compatible provider can be called through the live path. Real provider quality remains unverified until keys are supplied and genuine runs complete.
- Both pointwise and pairwise methods retain evidence references and judge versions.
- Swapped-order disagreements and per-example results appear in the report.
- Human reviews are stored separately; a shared team token does not prove reviewer identity or independence. Adjudicated gold labels require team review.
- Statistical tests and API tests exercise actual code paths. CI runs without paid provider calls.
- Dataset provenance, missing calibration, deployment limits, and unmeasured results are documented.

## Attribution and integration

The user is implementing on behalf of the team. Branch ownership is not evidence of individual authorship. Teammate author identities remain pending their agreed names and Git-linked emails. Until confirmed, commits use Dpkch06. Do not invent identities, reviews, human labels, or contribution claims.

Keep each workstream's changes on its own branch, then integrate them through reviewed pull requests. Shared contracts belong to the judge-engine branch; other workstreams depend on its commit. Do not duplicate shared files in conflicting branch histories.

## Outstanding course evidence

The software cannot create genuine team-authored cases or independent human reviews on the team's behalf. The first version includes their workflow, not fabricated completion. Live model measurements, the held-out study, load-test evidence, deployment, and presentation follow once inputs and credentials are available.
