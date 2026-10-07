import pytest
from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only')
    monkeypatch.setenv('SUPPORTJUDGE_CONFIG','openrouter.json')
    with TestClient(create_app(Store(tmp_path/'test.db'),start_worker=False)) as client:
        yield client


def test_local_actions_need_no_team_token(client):
    assert client.get('/api/health').status_code == 200
    response=client.post('/api/runs',json={'mode':'live','dataset':'support-v1'})
    assert response.status_code == 202
    assert client.get('/api/runs/'+response.json()['id']).json()['state'] == 'pending'


def test_unknown_split_and_path_traversal(client):
    assert client.post('/api/runs',json={'mode':'demo','dataset':'support-v1'}).status_code == 422
    assert client.post('/api/runs',json={'dataset':'../../secret'}).status_code == 422


def test_missing_run_and_promotion_rejected(client):
    assert client.get('/api/runs/missing').status_code == 404
    run=client.post('/api/runs',json={'mode':'live','dataset':'support-v1'}).json()
    assert client.post('/api/runs/'+run['id']+'/promote').status_code == 409


def test_append_only_reviews_and_interrupt(tmp_path):
    store=Store(tmp_path/'test.db');run_id=store.create_run({})
    assert store.claim()['id'] == run_id
    store.interrupt()
    assert store.run(run_id)['state'] == 'failed'
    store.annotate(run_id,{'reviewer':'one'});store.annotate(run_id,{'reviewer':'two'})
    assert len(store.annotations(run_id)) == 2


def test_live_dataset_listing_and_numbered_experiments(client):
    assert all(d['name'] != 'demo' for d in client.get('/api/datasets').json())
    first=client.post('/api/runs',json={'mode':'live','dataset':'support-v1','answer_source':'generate'}).json()
    second=client.post('/api/runs',json={'mode':'live','dataset':'support-v1','answer_source':'generate'}).json()
    rows=client.get('/api/experiments').json()
    assert [(r['id'],r['number']) for r in rows]==[(second['id'],2),(first['id'],1)]
    roles=client.get('/api/model-roles').json()
    assert len(roles['generators'])==2 and len(roles['judges'])==2
    assert client.post('/api/runs',json={'mode':'live','dataset':'demo'}).status_code==422
