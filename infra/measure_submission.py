"""Measure HTTP submission separately from model execution, using a disposable DB."""
import concurrent.futures
import gc
import json
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from supportjudge_api.api import create_app
from supportjudge_api.store import Store
from supportjudge_statistics.stats import percentile


def main():
    with tempfile.TemporaryDirectory(prefix='supportjudge-benchmark-') as directory:
        store = Store(Path(directory) / 'benchmark.db')
        server = uvicorn.Server(uvicorn.Config(create_app(store, start_worker=False), host='127.0.0.1', port=8019, log_level='error'))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.1)
            if not server.started:
                raise RuntimeError('Benchmark server did not start')
            payload = {'mode': 'live', 'dataset': 'support-v1', 'split': 'heldout', 'answer_source': 'generate', 'configuration': 'measurement-v1'}
            observations = []
            with httpx.Client(base_url='http://127.0.0.1:8019', timeout=30) as client:
                client.get('/api/health').raise_for_status()
                def submit(_):
                    start = time.perf_counter()
                    response = client.post('/api/runs', json=payload)
                    return {'seconds': time.perf_counter()-start, 'status': response.status_code}
                started = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    for batch in range(20):
                        observations.extend(pool.map(submit, range(5)))
                        # Cleanup is outside each request timer. No worker or model calls run.
                        with store.connection() as db:
                            db.execute('DELETE FROM runs')
                        db.close()
                wall = time.perf_counter()-started
            durations = [x['seconds'] for x in observations]
            result = {'scope': 'Loopback HTTP POST /api/runs, real validation and SQLite writes, five concurrent clients, worker disabled, disposable DB. Excludes model execution and queue drain.',
                      'requests': len(observations), 'concurrency': 5, 'errors': sum(x['status'] != 202 for x in observations),
                      'p50_seconds': percentile(durations, .5), 'p95_seconds': percentile(durations, .95), 'p99_seconds': percentile(durations, .99),
                      'wall_seconds_including_batch_cleanup': wall, 'observations': observations}
            Path('reports/submission-measurements.json').write_text(json.dumps(result, indent=2))
            print(json.dumps({k:v for k,v in result.items() if k != 'observations'}, indent=2))
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            gc.collect()


if __name__ == '__main__':
    main()
