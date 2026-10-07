# Support dataset v1

`data/evals/support-v1.json` contains 60 distinct customer scenarios and 120 candidate answers. The cases, answers, source paraphrases, and labels are AI-authored. Nobody has independently reviewed the labels. Their status is `ai_authored`, and the reviewer lists are empty.

Use these fixtures to exercise the workflow and report agreement against provisional references. Do not report that agreement as human calibration. A high score against these labels does not establish judge reliability.

## Split and scope

Development contains 30 scenarios about cancellation, refunds, and billing lookup. Heldout contains 30 scenarios about file recovery, account access, and support channels. All ten scenarios in each policy family remain in the same split. This avoids putting rewritten variants of the same policy rule on both sides. It also makes heldout evaluation a test of generalization to new policy families, rather than a random sample of familiar topics.

The scope is individual Basic and Plus support. Some source articles cover other plans, but their entitlements are not assigned to Basic or Plus. Cases use stated standard recovery periods and explicitly mention add-on absence where it matters. Regional refund cases give the country and purchase age. Missing details require clarification instead of a promised refund.

Within each family, eight scenarios compare a policy-correct answer with a faulty one. Correct answers alternate between A and B. One scenario has two acceptable answers, and one has two equally unacceptable answers. Both final scenarios have a pairwise tie, demonstrating that a tie does not mean acceptance. Two heldout cases include evaluator-manipulation text. There are 24 A preferences, 24 B preferences, and 12 ties. There are no provisional insufficient-evidence preferences in this version.

## Source records

`data/policies/manifest.json` records six official source URLs, their displayed update dates, retrieval date, evidence text, and SHA-256 hashes. These hashes freeze our paraphrases. They do not prove that a whole webpage was archived. Retrieval occurred on 2026-10-07. The official webpages can change afterward.

Rebuild with `python data/build_support_dataset.py`. The script owns only the dataset and policy manifest. Inspect the generated diff before accepting a rebuilt dataset.

## Human review

Two teammates should independently read each question, candidate answer, and policy evidence. Each must label both answers accept or reject, choose A, B, tie, or insufficient evidence, and record a policy-based rationale. Reviewers should not use model verdicts as their answer key. Resolve disagreements after both reviews, retain the original records, and correct source paraphrases where needed.

Do not change `ai_authored` to `human_reviewed` merely to unlock a release check. The review records must exist, and the reviewers must actually inspect the examples. These review labels apply to the fixture answers; generated answers need their own reviews.

## Limits

The cases are synthetic, short, and usually contain explicit contradictions. They do not represent actual support traffic, language variation, prevalence of failures, or a validated benchmark. Evidence is included directly, so this evaluates answering and judging rather than retrieval. The six family groups reduce the effective variety compared with 60 unrelated tasks. Bootstrap ranges over scenarios do not capture every kind of dependence or real-world uncertainty. No heldout cases have yet been used to tune a live judge, but maintain that separation when live experiments begin.
