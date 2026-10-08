"""Measure local HTTP overhead. Does not measure hosted-model throughput."""
import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path

import httpx
from supportjudge_statistics.stats import percentile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--requests',type=int,default=100)
    parser.add_argument('--concurrency',type=int,default=5)
    parser.add_argument('--output',default='reports/local-load.json')
    args=parser.parse_args()
    def request(_):
        start=time.perf_counter()
        with httpx.Client(timeout=10) as client:
            response=client.get(args.url+'/api/health');response.raise_for_status()
        return time.perf_counter()-start
    started=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        times=list(pool.map(request,range(args.requests)))
    elapsed=time.perf_counter()-started
    result={'scope':'Actual local health endpoint HTTP load, including client connection overhead; not LLM throughput',
            'requests':args.requests,'concurrency':args.concurrency,'elapsed_seconds':elapsed,
            'requests_per_second':args.requests/elapsed,'p50_seconds':percentile(times,.5),'p99_seconds':percentile(times,.99)}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
