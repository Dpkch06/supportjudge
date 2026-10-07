"""Export a completed report as a standalone, shareable HTML leaderboard."""
import argparse
import html
import json
from pathlib import Path


def escape(value):
    return html.escape(str(value))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('report')
    parser.add_argument('--output',default='reports/leaderboard.html')
    args=parser.parse_args();report=json.loads(Path(args.report).read_text(encoding='utf-8'))
    rows=''.join('<tr>'+''.join('<td>'+escape(x)+'</td>' for x in (r['judge'],r['system'],r['mean_score'],r['score_interval'],r['wins']))+'</tr>' for r in report['leaderboard'])
    cases=''
    for r in report['rows']:
        cases+=f"<details><summary>{escape(r['case_id'])} / {escape(r['judge'])} / {escape(r['preference'])}</summary><p>{escape(r['question'])}</p>"
        for name,answer in r['answers'].items():
            cases+=f"<h3>Answer {escape(name)}</h3><pre>{escape(answer)}</pre><p>{escape(r['points'][name]['verdict'])}: {escape(r['points'][name]['reason'])}</p>"
        for e in r['evidence']:
            cases+=f"<pre>{escape(e['text'])}</pre><p>{escape(e['url'])}</p>"
        cases+=f"<p>Order consistent: {escape(r['order_consistent'])}. Label status: {escape(r['labels'].get('status','unreviewed'))}.</p></details>"
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SupportJudge report</title>
    <style>body{{max-width:1000px;margin:40px auto;padding:20px;font:16px/1.5 system-ui;color:#19382f;background:#f3f6f4}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccc}}details{{padding:15px;background:white;margin:12px 0}}summary{{cursor:pointer}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.notice{{background:#fff0c9;padding:18px}}</style>
    <h1>SupportJudge comparison report</h1><p class="notice">Mode: {escape(report['mode'])}. {escape(report['dataset_provenance'])}. Release approval: {escape(report['gate']['passed'])}.</p>
    <h2>Answer leaderboard</h2><table><tr><th>Judge</th><th>System</th><th>Mean / 4</th><th>Scenario interval</th><th>Consistent wins</th></tr>{rows}</table>
    <h2>Judge quality</h2><pre>{escape(json.dumps(report['calibration'],indent=2))}</pre><h2>Provisional references</h2><pre>{escape(json.dumps(report.get('provisional_reference',[]),indent=2))}</pre>
    <h2>Inspect evidence and disagreements</h2>{cases}<h2>Versions and measurements</h2><pre>{escape(json.dumps({'versions':report['versions'],'metrics':report['metrics']},indent=2))}</pre></html>'''
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8');print(path)


if __name__=='__main__':
    main()
