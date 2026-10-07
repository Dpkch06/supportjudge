# Run the first version

The first version is a local application with a static frontend, FastAPI, one worker thread, SQLite, JSON reports, and an OpenAI-compatible model adapter. Run commands from the repository root.

```powershell
python -m pip install -e '.[dev]'
$env:SUPPORTJUDGE_TEAM_TOKEN = 'a-long-random-team-token'
python -m supportjudge_cli.cli serve
```

Open http://127.0.0.1:8000. Enter the team token in the experiment form and start the offline demo. The browser stores the token only in the current page input. API documentation is at /docs.

```powershell
python -m pytest -q
python -m supportjudge_cli.cli evaluate --output reports/demo.json
python -m supportjudge_cli.cli evaluate --gate
```

The last command deliberately exits 1. Simulated evaluations must never approve a real release. Other evaluation failures exit 2. No runnable commands require a teammate's GitHub credentials.

## Live evaluation

Copy configs/judges/live.example.json to configs/judges/live.json. Replace both judge model identifiers with distinct available models, configure provider base URLs and key environment names, and set answer-model IDs when generating answers. Enter current token prices if you want cost estimates; unknown pricing stays null rather than appearing as zero.

Set provider keys locally. Do not send keys in chat or commit them. The adapter uses POST /chat/completions with JSON output and a 90-second timeout. It expects an OpenAI-compatible response; providers with other APIs require an adapter. See the official [Chat Completions reference](https://developers.openai.com/api/reference/resources/chat).

```powershell
$env:OPENAI_API_KEY = 'your-key'
python -m supportjudge_cli.cli evaluate --mode live --output reports/live.json
python -m supportjudge_cli.cli evaluate --mode live --answers generate --output reports/generated.json
```

The committed demo data has no human labels and therefore cannot pass calibration even with live judges. Add independently reviewed fixed-answer labels to a separate dataset before measuring human agreement. Generated answers are unreviewed; labels for fixture answers cannot be transferred to newly generated answers.

## Data and review

Add a JSON dataset under data/evals/ with the structure in demo.json. Mark AI-generated material accurately. Do not use real tickets or secrets; report read endpoints are public in this first version. Gold labels require status human_reviewed, two distinct reviewer names, verdicts, and an adjudication rationale. The application cannot verify that names represent two different people; the team must verify independence.

Browser reviews append records to the database. They do not silently update gold labels. Export through the authenticated annotations endpoint, independently adjudicate, then import a new dataset version. Public case data contains fictional scenarios only.

## Operations and limitations

Use one application worker only. Each run stores a snapshot of its dataset and configuration. On restart, interrupted running jobs fail explicitly; pending jobs remain queued. Cached completed calls allow a newly submitted run to reuse results. No automatic retries risk undisclosed duplicate charges. A provider timeout can still incur charges even if no answer was received.

Each report contains per-call traces, reported token usage, optional estimated cost, actual model identifiers, hashes, code commit, and p50/p99 call latency. These are local traces, not a Langfuse integration. Bootstrap intervals cover scenario sampling only. No live-provider quality measurements, genuine human calibration, load tests, online drift study, or public deployment have been completed.

Configuration approval is recorded by the authenticated promotion endpoint only after a live report passes the conservative gate. It does not automatically deploy or change the live settings file. To compare a new judge in shadow mode, run the same fixture dataset with a separate live configuration; to roll back, restore the previous versioned configuration. Automated online sampling and deployment rollback remain follow-up work.

The GitHub workflow runs tests and demo checks without secrets. It is not a protected production release gate until configured as a required check and connected to a trusted live evaluation dataset. Keep live.json local and version a sanitized copy of real configuration before reporting reproducible release results.
