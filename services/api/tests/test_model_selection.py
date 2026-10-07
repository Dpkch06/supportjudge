import pytest
from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store
from supportjudge_api import model_selection
from supportjudge_evaluation.files import load_settings
from supportjudge_evaluation.models import Request


def model_catalog():
    return [{"id":m,"name":m,"judge_supported":True,"input_per_million":1,"output_per_million":2} for m in model_selection.AUTO_POOL]


def test_rotation_excludes_generators_and_previous_pair():
    settings=load_settings("live","openrouter")
    request=Request(mode="live",judge_selection="rotate")
    first=model_selection.resolve(settings,request,model_catalog())
    second=model_selection.resolve(settings,request,model_catalog(),[j.model for j in first.judges])
    assert {m.model for m in first.judges} != {m.model for m in second.judges}
    for resolved in [first,second]:
        assert not {m.model for m in resolved.judges} & {m.model for m in resolved.answer_models}
        assert len({m.model.split('/')[0] for m in resolved.judges})==2


def test_manual_self_judging_and_unknown_models_rejected():
    settings=load_settings("live","openrouter")
    for judges in [[settings.answer_models[0].model,'anthropic/claude-haiku-4.5'],['unknown/model','deepseek/deepseek-chat-v3.1']]:
        with pytest.raises(ValueError):
            model_selection.resolve(settings,Request(judge_selection="manual",judge_models=judges),model_catalog())


def test_rotation_persists_across_submissions(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only')
    monkeypatch.setenv('SUPPORTJUDGE_CONFIG','openrouter.json')
    monkeypatch.setattr(model_selection,'catalog',model_catalog)
    store=Store(tmp_path/'test.db')
    payload={'mode':'live','dataset':'support-v1','answer_source':'generate','judge_selection':'rotate'}
    with TestClient(create_app(store,start_worker=False)) as client:
        first=client.post('/api/runs',json=payload)
        second=client.post('/api/runs',json=payload)
        assert first.status_code==second.status_code==202
        assert set(first.json()['judges'])!=set(second.json()['judges'])
        snapshot=store.run(second.json()['id'])['request']['settings_snapshot']
        assert [m['model'] for m in snapshot['judges']]==second.json()['judges']
    with TestClient(create_app(store,start_worker=False)) as client:
        third=client.post('/api/runs',json=payload)
        assert set(third.json()['judges'])!=set(second.json()['judges'])
        assert client.post('/api/runs',json={**payload,'judge_selection':'manual','judge_models':['unknown/model','unknown/other']}).status_code==422
