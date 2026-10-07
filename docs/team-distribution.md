# Team distribution

The six workstreams below have assigned owners and different reviewers. Ownership identifies who reviews and maintains the component. Commit authorship remains separate and will use confirmed details only. VinayakPaka and omwagh28 had pending repository invitations when this plan was created.

| Workstream | Owner | Reviewer | Responsibilities | First deliverable |
| --- | --- | --- | --- | --- |
| Domain and human evaluation | @Navneet-Scaler | @VinnuReddy18 | Policy manifest, scenarios, independent labels, adjudication, split control | Reviewed policy subset and 10-case pilot |
| Judge engine and rubrics | @Vijaygaurav2004 | @Dpkch06 | Provider adapters, pointwise/pairwise prompts, swapping, validation, judge configuration | Two judges scoring fixed pilot answers |
| Statistics and release checks | @omwagh28 | @Vijaygaurav2004 | Agreement metrics, false acceptance/rejection, bootstrap intervals, release policy, CLI and CI | Reproducible report and intentionally failing regression |
| Backend and job processing | @VinnuReddy18 | @VinayakPaka | API contracts, v1 SQLite persistence and future PostgreSQL schema, job lifecycle, retries, access controls | Submit, process, and retrieve a run |
| Frontend and report experience | @VinayakPaka | @Navneet-Scaler | Leaderboard, example inspection, judge comparisons, review interaction | Report view wired to agreed contracts |
| LLMOps and integration | @Dpkch06 | @omwagh28 | Tracing, deployment, shadow comparison, rollback, load testing, reproducibility | Traceable vertical slice and rollback evidence |

## Directory ownership

| Member | Owned paths |
| --- | --- |
| Navneet-Scaler | data/, docs/domain/ |
| Vijaygaurav2004 | packages/evaluation/, configs/judges/, configs/rubrics/ |
| omwagh28 | packages/statistics/, configs/releases/ |
| VinnuReddy18 | services/api/, services/worker/ |
| VinayakPaka | apps/web/ |
| Dpkch06 | infra/, .github/, root setup files, integration docs |

Tests live inside their owner's directory. Shared root files have one owner. Branches keep separate path changes; API and data contracts are agreed through the evaluation schemas. No implementation commits are pushed or merged until requested.

## Shared work

All teammates author cases and independently review someone else's labels. Agree on the rubric before expanding the dataset. No author supplies both supposedly independent labels. Resolve disagreements with source evidence and preserve original labels.

All teammates contribute to README measurements, architecture reasoning, demonstration, and presentation. The domain owner controls held-out access until final configurations are frozen. The coordinator is @Dpkch06 to resolve interface and schedule dependencies; coordination is not ownership of every component.

## Interfaces to agree first

- Domain and judge owners agree on scenario, evidence, answer-fixture, and annotation records.
- Judge and statistics owners agree on verdicts, scores, preferences, errors, and swapped-order identity mapping.
- Backend and evaluation owners agree on run input, pinned versions, job states, retry behavior, and report output.
- Frontend and backend owners agree on API responses, progress states, review permissions, and incomplete-result behavior.
- LLMOps and statistics owners agree on trace identifiers, metric definitions, CI credentials, and release-check exit codes.

## Milestones and review evidence

| Milestone | Completion evidence | Owner and date |
| --- | --- | --- |
| Scope and contracts | Reviewed README, named owners, schema examples, policy subset | [Name / date] |
| Human pilot | 10 authored development cases with independent labels and adjudication | [Name / date] |
| Evaluation slice | Two answer prompts, two judges, both scoring methods, inspectable report | [Name / date] |
| Dataset and statistics | Split manifest, category metrics, uncertainty, reproducible run | [Name / date] |
| CI and operations | Separate judge/answer checks, failed regression, traces, shadow comparison, rollback | [Name / date] |
| Final evidence | Frozen held-out evaluation, measured latency/cost/throughput, published leaderboard | [Name / date] |
| Presentation | 15-minute rehearsal, shared speaking roles, prepared Q&A | [Name / date] |

## Working agreements

Use an issue for a bounded deliverable and a pull request for review. Include the problem, proposed behavior, completion evidence, and dependencies. Avoid parallel edits to shared contracts without agreement. Changes to dataset splits, rubrics, judges, or thresholds must explain their effect on previous comparisons.

Do not label mocked results as measured API results. Do not claim a protected merge check until branch rules actually require it. Never commit secrets or real customer data. Record decisions in docs/decisions with alternatives, reason, and evidence.

The first implementation task is the human pilot plus a minimal evaluation slice. Frontend and backend planning can proceed against agreed contracts, but we should prove judging works before expanding infrastructure.
