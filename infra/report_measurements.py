"""Write measured results from a completed live run and the submission benchmark."""
import argparse
import json
from pathlib import Path

from supportjudge_api.store import Store
from supportjudge_statistics.stats import percentile


def distribution(values):
    return {f'p{int(q*100)}': percentile(values, q) for q in (.5, .95, .99)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id')
    args = parser.parse_args()
    run = Store().run(args.run_id)
    if not run or run['state'] != 'completed':
        raise SystemExit('A completed live run is required; failed or pending jobs are not valid measurements.')
    report = run['report']
    request = run['request']['parameters']
    rows, traces = report['rows'], report['traces']
    cases = list(dict.fromkeys(r['case_id'] for r in rows))
    calls_per_case = len(run['request']['settings_snapshot']['judges'])*4 + (2 if request['answer_source']=='generate' else 0)
    assert len(traces) == len(cases)*calls_per_case, 'Unexpected call structure'
    live = [t for t in traces if not t['cache_hit']]
    case_seconds = [sum(t['latency_seconds'] for t in traces[i:i+calls_per_case]) for i in range(0,len(traces),calls_per_case)]
    cost = report['metrics']['cost_usd']
    submission = json.loads(Path('reports/submission-measurements.json').read_text())
    models = {}
    for model in sorted({t['model'] for t in live}):
        group = [t for t in live if t['model']==model]
        models[model] = {'calls':len(group), 'tokens':sum(t['tokens'] for t in group),
                         'cost_usd':sum(t['cost_usd'] for t in group) if all(t['cost_usd'] is not None for t in group) else None,
                         'zero_cost_calls':sum(t['cost_usd']==0 for t in group),
                         'latency_seconds':distribution([t['latency_seconds'] for t in group])}
    elapsed = report['elapsed_seconds']
    results = {'run_id':args.run_id,'split':request['split'],'cases':len(cases),'calls':len(traces),'uncached_calls':len(live),
               'elapsed_seconds':elapsed,'cases_per_minute':len(cases)/elapsed*60,'tokens':report['metrics']['tokens'],
               'cost_usd':cost,'cost_per_case_usd':cost/len(cases) if cost is not None else None,
               'call_latency_seconds':distribution([t['latency_seconds'] for t in live]),
               'per_case_provider_time_seconds':distribution(case_seconds),'queue_wait_seconds':None,
               'case_timings':[{'case_id':cid,'provider_seconds':seconds} for cid,seconds in zip(cases,case_seconds)],
               'models':models,'submission':submission,'leaderboard':report['leaderboard'],'calibration':report['calibration']}
    Path('reports/final-measurements.json').write_text(json.dumps(results,indent=2))
    Path('reports/heldout-measurement-run.json').write_text(json.dumps(run,indent=2))
    lines = ['# Measurement report', '', f"Run `{args.run_id}`, recorded {report['created']}. Split: {request['split']}. Configuration: `{request['configuration']}`.", '',
             '## Scope', '', f'{len(cases)} questions, two live generators, two live judges, and both answer orders. Settings were frozen from Experiment 5 before this run. No rubric tuning used these results.', '',
             '## Operational results', '', '| Measure | Result |', '| --- | --- |',
             f"| Submission requests / concurrency / errors | {submission['requests']} / {submission['concurrency']} / {submission['errors']} |",
             f"| Submission p50 / p95 / p99 | {submission['p50_seconds']} / {submission['p95_seconds']} / {submission['p99_seconds']} seconds |",
             f'| Completed model calls / cache hits | {len(live)} / {len(traces)-len(live)} |',
             f'| Evaluation duration | {elapsed:.2f} seconds |',
             f"| Throughput | {results['cases_per_minute']:.3f} questions/minute |",
             f"| Model-call p50 / p95 / p99 | {results['call_latency_seconds']} seconds |",
             f"| Per-question provider-time p50 / p95 / p99 | {results['per_case_provider_time_seconds']} seconds |",
             '| Queue wait | Not instrumented |', f"| Tokens | {results['tokens']} |",
             f'| Recorded cost / cost per question | ${cost:.6f} / ${cost/len(cases):.6f} |' if cost is not None else '| Cost | Incomplete provider cost reporting |', '',
             'Submission timing uses a separate loopback HTTP server with the real validation and SQLite persistence, five concurrent clients and its worker disabled. It excludes model execution. The live run uses the normal single-worker app. Per-question time sums its sequential provider calls and excludes local processing. Queue wait was not instrumented; saved timestamps cannot separate it reliably from report aggregation.', '',
             '## Model breakdown', '', '| Model | Calls | Tokens | Recorded USD | Latency p50 / p95 / p99 seconds |', '| --- | --- | --- | --- | --- |']
    for model,m in models.items():
        lines.append(f"| {model} | {m['calls']} | {m['tokens']} | {m['cost_usd']} | {m['latency_seconds']} |")
    lines += ['', '## Judge scores', '', '| Judge | Answer | Mean score out of 4 | 95% bootstrap interval | Questions |', '| --- | --- | --- | --- | --- |']
    for item in report['leaderboard']:
        lines.append(f"| {item['judge']} | {item['system']} | {item['mean_score']} | {item['score_interval']} | {item['cases']} |")
    lines += ['', '| Judge | Swapped-order consistency | Mean B minus A | 95% paired interval |', '| --- | --- | --- | --- |']
    for item in report['calibration']:
        lines.append(f"| {item['judge']} | {item['order_consistency']:.1%} | {item['paired_delta_B_minus_A']} | {item['paired_delta_interval']} |")
    lines += ['', '## Interpretation and limits', '',
              f"- Submission p95 target of 500 ms: {'met' if submission['p95_seconds']<.5 else 'missed'} in this local test.",
              f"- Per-question provider-time p95 target of 60 seconds: {'met' if results['per_case_provider_time_seconds']['p95']<60 else 'missed'}. Full end-to-end question latency was not instrumented.",
              '- This completed run has no failed model calls recorded. It is one run, not a long-term reliability estimate. Historical failed experiments are excluded; their partial costs are not fully recoverable from saved reports.',
              '- Bootstrap intervals use 1,000 question-level resamples with seed 42. Related questions share policies; these intervals do not account for policy-family clustering or repeated model sampling.',
              '- Scores and agreement between judges are not human-verified accuracy. Human calibration, false acceptance and false rejection for these generated answers remain unmeasured.',
              '- Model IDs, prompts, rubric, dataset hash and implementation hash are saved in the raw run. Providers control model revisions and sampling defaults, so exact output reproduction is not guaranteed.',
              '- Generator prompts differ as saved in Experiment 5. Results compare answer configurations, not model identity alone.',
              '- Once inspected, this held-out set must not be described as unseen evidence for later tuning.',
              '- API acceptance measurements do not establish sustained load capacity with a busy worker. Cost reflects recorded provider charges or configured estimates, not an account-wide invoice. Some providers returned zero cost for nonzero token usage; these zeros are preserved and may understate actual billing. Per-model zero-cost call counts are included in the JSON.', '',
              'Raw artifacts: `reports/final-measurements.json`, `reports/heldout-measurement-run.json`, `reports/submission-measurements.json`. Rerun the report with `python infra/report_measurements.py '+args.run_id+'`.']
    Path('reports/measurement-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in results.items() if k not in ('submission','leaderboard','calibration','models','case_timings')},indent=2))


if __name__ == '__main__':
    main()
