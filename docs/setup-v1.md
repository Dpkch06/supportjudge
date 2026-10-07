# Run SupportJudge

Run commands from the repository root. Copy .env.example to .env, set OPENROUTER_API_KEY, and keep SUPPORTJUDGE_CONFIG=openrouter.json. The app loads .env automatically; Git ignores it.

```powershell
python -m pip install -e '.[dev]'
python -m supportjudge_cli.cli serve
```

Open http://127.0.0.1:8000. Select the support dataset and development or held-out split, then click Run comparison. No team token is required. The server binds to localhost and uses one worker. Saved experiments remain in SQLite after restart.

## Model roles

Choose Generator A and Generator B from the OpenRouter catalog. The default generators are GPT-4.1 mini and Gemini 2.5 Flash. Automatic mode rotates across available Claude, DeepSeek, Mistral, Gemini and GPT judges, excluding both generator model IDs. Consecutive automatic experiments use different judge pairs. Manual mode lets you choose two distinct JSON-capable judges. Both judges score both answers and compare them in both orders. Selected IDs and current pricing are pinned in each run.

The A and B prompts still differ. A model comparison therefore changes both prompt and model unless you align the prompts in the configuration. To measure a rubric change, keep the judges and generated answers fixed. Catalog compatibility does not guarantee every provider will return valid output; failed evaluations remain failed.

The page shows numbered experiments, scores, confidence intervals, order consistency, disagreements, evidence, and downloadable reports. It omits human-review and release-approval controls. Underlying reports retain dataset provenance. Without reviewed reference verdicts, human agreement and false-acceptance rates cannot be measured.

## Command line and checks

```powershell
python -m pytest -q
python -m supportjudge_cli.cli evaluate --output reports/live.json
```

The CLI defaults to live models, generated answers, support-v1, and development. Internal deterministic test doubles remain for repeatable unit tests; the app and CLI do not offer an offline evaluation mode. The normal CI workflow runs tests without API keys. Provider failures exit 2. The optional CLI release gate exits 1 when its calibration requirements are unmet.

## Operations

Each report pins the dataset and settings hashes and records model identifiers, token counts, cost, cache usage, and call latency. OpenRouter reported cost takes precedence over estimates from configured token prices. Cached calls incur no new provider charge. Run only one application worker. Interrupted running jobs fail explicitly on restart; pending jobs remain queued. No automatic retry conceals duplicate charges.

The first completed live run evaluated 30 fixed answer pairs with two judges and both answer orders, for 240 calls. New browser runs generate both answers first. Human calibration, an online drift study, and public deployment remain pending.

## Edit a saved rubric

Click an experiment number to open its page. The page loads the saved generator models, judge models, prompts and exact rubric. Edit the score descriptions directly or choose a stricter starting point, give the comparison a name, and click Run rubric comparison. Reset restores the original descriptions. An unchanged rubric cannot start a comparison.

A comparison reuses the original answers and policy evidence, pins judge models and instructions, and changes only the rubric. It creates a separate saved experiment. The results show edited descriptions, per-dimension score differences, pairwise preference changes and judge explanations. Reloading a comparison URL restores its results. Single reruns still include model sampling variation, so a changed score alone is not conclusive causal evidence.
