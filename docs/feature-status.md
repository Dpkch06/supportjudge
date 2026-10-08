# Feature status

Checked against the original README scope and the local implementation on October 8, 2026. Working code and completed measurements are listed separately.

| Feature | Status | Evidence or remaining work |
| --- | --- | --- |
| Compare generated support answers | Working | Two generators, separate prompts, common question and policy evidence. Both live generators have completed runs. |
| Choose generators and judges | Working | OpenRouter catalog selectors, separate generator and judge roles, manual choice or rotating judge pairs. Exact generator model IDs cannot also be judges in these runs. |
| Multiple judges | Working | Separate scores and preferences for each judge. This measures disagreement, not which judge is correct. |
| Pointwise and pairwise evaluation | Working | Four dimension scores per answer; A/B/tie/insufficient pairwise judgments. |
| Position bias checks | Working | Reverse answer order, map preferences back, flag inconsistent results. |
| Bootstrap confidence intervals | Partial | Scenario-level intervals exist. Policy-family clustering and repeat-run uncertainty are not modeled. |
| Versioned rubrics | Working per experiment | Saved rubric fields are editable; each named comparison stores a new settings snapshot and links to its baseline. A reusable cross-project rubric library remains optional work. |
| Rubric-change experiment | Working | Dedicated experiment page freezes saved answers, evidence and judges, edits all score descriptions, and shows rubric edits, score deltas, preferences and explanations. A live check completed with eight judge calls and no generation calls. |
| Judge-version comparison | Rubric versions working | Dedicated page compares the same judges across saved rubric versions on frozen answers. A controlled judge-model replacement study remains optional. |
| Human calibration | Workflow ready; team reviews pending | Blind X/Y review, two reviewer names, immutable submissions, adjudication and per-judge agreement/false-acceptance/false-rejection metrics. Browser flow checked using disposable test records. No real human-reviewed reference set yet; this workflow does not update release approval. |
| Human-written answers as a candidate | Optional extension | Distinct from calibration. Importing human-written support answers into a comparison is not a built-in browser workflow. |
| Domain dataset and policy provenance | Partial course evidence | Versioned scenarios, policy sources, hashes, and development/held-out splits exist. Team authorship and independent review remain unverified. |
| Per-example leaderboard | Working locally | Score tables, policy evidence, reasons, order sensitivity, disagreement filter, JSON export. No public leaderboard deployment. |
| Reproducible runs | Partial | Dataset/settings snapshots, hashes, model IDs, code hash, timestamps and cached calls exist. Controlled sampling parameters and provider-version pinning need work. |
| Reusable service and CI gate | Partial | API, CLI, remote CI example and conservative gate logic exist. No demonstrated required GitHub check blocking a real regression in another repository. |
| Judge approval and rollback | Backend only | Approval/activation records exist; calibration blocks approval. End-to-end calibrated promotion and deployment rollback are unverified. Controls removed from the current UI. |
| Observability | Partial | Tokens, cost, cache hits, call latency and local API counters exist. No Langfuse integration, complete queue/failure dashboard, or alerting. |
| Online sampling and drift | Remaining | A simulated traffic flag and category counts are not a real live-support sampling pipeline or validated drift detector. |
| Performance evidence | Local measurements complete; queue timing pending | 100 submissions at concurrency 5: p95 48.6 ms, zero errors. Held-out run: 300 live calls, 16.3 minutes, 1.839 questions/minute; provider-time p95 per question 40.6 seconds. Queue wait and full end-to-end per-question timing were not instrumented. See reports/measurement-report.md. |
| Final held-out study | Model evaluation complete; human calibration pending | Experiment 8 evaluated all 30 held-out questions with the frozen Experiment 5 configuration. Report includes score intervals, order sensitivity, timing and cost limitations. Independent review of these generated answers remains. |
| Presentation and submission package | Remaining | Architecture diagram aligned with the shipped system, final measured README, presentation, resume bullets and team-authored peer reviews. |

## Next sequence

1. Run a larger rubric-impact study using the implemented frozen-answer comparison.
2. Extend frozen-answer comparisons to judge-model changes; hold the rubric fixed for that study.
3. Have two teammates independently review the same saved answers in Human review, adjudicate them, and measure judge agreement.
4. Demonstrate CI blocking a known regression; complete held-out measurements and publish the leaderboard and presentation.

Automatic judge rotation is for exploration. A controlled rubric experiment must pin its judges. Rotating judges and changing a rubric at the same time confounds the result.
