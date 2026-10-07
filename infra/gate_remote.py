"""Call a deployed SupportJudge instance from another repository's CI."""
import argparse
import json
import time
from pathlib import Path

import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--dataset',default='support-v1')
    parser.add_argument('--split',choices=['development','heldout'],default='development')
    parser.add_argument('--timeout',type=int,default=600)
    parser.add_argument('--output',default='reports/remote-gate.json')
    args=parser.parse_args()
    with httpx.Client(base_url=args.url.rstrip('/'),timeout=30) as client:
        response=client.post('/api/runs',json={'mode':'live','dataset':args.dataset,'split':args.split,'answer_source':'fixtures'})
        response.raise_for_status();run_id=response.json()['id'];deadline=time.monotonic()+args.timeout
        while time.monotonic()<deadline:
            response=client.get('/api/runs/'+run_id);response.raise_for_status();run=response.json()
            if run['state']=='failed':
                raise SystemExit(2)
            if run['state']=='completed':
                report=run['report'];path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(report,indent=2),encoding='utf-8')
                raise SystemExit(0 if report['mode']=='live' and report['gate']['passed'] else 1)
            time.sleep(2)
    raise SystemExit(2)


if __name__=='__main__':
    main()
