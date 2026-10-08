from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store
from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import load_dataset, load_settings
from supportjudge_evaluation.models import Request


def test_configuration_history_rolls_back(tmp_path):
    store=Store(tmp_path/'test.db')
    store.promote('first','hash-first');store.promote('second','hash-second')
    approvals=store.promotions()
    first=next(p for p in approvals if p['run_id']=='first')
    second=next(p for p in approvals if p['run_id']=='second')
    store.activate(first['id']);assert store.active()['settings_hash']=='hash-first'
    store.activate(second['id']);assert store.active()['settings_hash']=='hash-second'
    store.activate(first['id']);assert store.active()['settings_hash']=='hash-first'


def test_operations_and_shadow_comparison(tmp_path,monkeypatch):
    store=Store(tmp_path/'test.db')
    report=evaluate(load_dataset('demo'),load_settings('demo'),Request(),store)
    ids=[]
    for _ in range(2):
        run=store.create_run({});store.finish(run,report=report);ids.append(run)
    with TestClient(create_app(store,start_worker=False)) as client:
        metrics=client.get('/api/observability').json()
        assert metrics['demo_runs']==2 and metrics['live_runs']==0
        result=client.get(f'/api/compare/{ids[0]}/{ids[1]}').json()
        assert not any(c['changed'] for c in result['examples'])
        assert client.post('/api/configuration/activate/missing').status_code==404


def test_online_single_case_request_and_invalid_selection(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only')
    monkeypatch.setenv('SUPPORTJUDGE_CONFIG','openrouter.json')
    store=Store(tmp_path/'test.db')
    with TestClient(create_app(store,start_worker=False)) as client:
        assert client.post('/api/runs',json={'mode':'live','dataset':'support-v1','case_id':'does-not-exist'}).status_code==422
        response=client.post('/api/runs',json={'mode':'live','dataset':'support-v1','case_id':load_dataset('support-v1').cases[0].id,'traffic':'simulated_online'})
        assert response.status_code==202
