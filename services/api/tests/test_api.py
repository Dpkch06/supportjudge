import pytest
from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SUPPORTJUDGE_TEAM_TOKEN','test-token')
    with TestClient(create_app(Store(tmp_path/'test.db'),start_worker=False)) as client:
        yield client


def test_team_access_and_public_health(client):
    assert client.get('/api/health').status_code == 200
    assert client.post('/api/runs',json={}).status_code == 401
    response=client.post('/api/runs',json={},headers={'X-Team-Token':'test-token'})
    assert response.status_code == 202
    assert client.get('/api/runs/'+response.json()['id']).json()['state'] == 'pending'


def test_unknown_split_and_path_traversal(client):
    headers={'X-Team-Token':'test-token'}
    assert client.post('/api/runs',json={'split':'heldout'},headers=headers).status_code == 422
    assert client.post('/api/runs',json={'dataset':'../../secret'},headers=headers).status_code == 422


def test_missing_run_and_promotion_rejected(client):
    assert client.get('/api/runs/missing').status_code == 404
    run=client.post('/api/runs',json={},headers={'X-Team-Token':'test-token'}).json()
    assert client.post('/api/runs/'+run['id']+'/promote',headers={'X-Team-Token':'test-token'}).status_code == 409


def test_append_only_reviews_and_interrupt(tmp_path):
    store=Store(tmp_path/'test.db');run_id=store.create_run({})
    assert store.claim()['id'] == run_id
    store.interrupt()
    assert store.run(run_id)['state'] == 'failed'
    store.annotate(run_id,{'reviewer':'one'});store.annotate(run_id,{'reviewer':'two'})
    assert len(store.annotations(run_id)) == 2
