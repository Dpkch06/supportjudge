from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store
from supportjudge_api.rubric_comparison import RubricChange, frozen_snapshot, changes
from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import load_dataset, load_settings
from supportjudge_evaluation.models import Request


def baseline(store):
    dataset=load_dataset('support-v1')
    settings=load_settings('demo')
    request=Request(dataset='support-v1',case_id=dataset.cases[0].id)
    report=evaluate(dataset,settings,request,store)
    report['mode']='live'
    report['answer_source']='generate'
    for row in report['rows']:
        row['answers']={'A':'Generated answer A','B':'Generated answer B'}
    request=request.model_copy(update={'mode':'live','answer_source':'generate','judge_selection':'rotate'})
    rid=store.create_run({'parameters':request.model_dump(),'dataset_snapshot':dataset.model_dump(),'settings_snapshot':settings.model_dump()})
    store.finish(rid,report=report)
    return store.run(rid)


def change_for(run):
    rubric=deepcopy(run['report']['versions']['settings_snapshot']['rubric'])
    rubric['faithfulness']['4']='All material claims must cite supplied policy evidence.'
    return RubricChange(rubric=rubric)


def test_freezes_generated_answers_and_models_without_mutating_baseline(tmp_path):
    run=baseline(Store(tmp_path/'test.db'))
    original=deepcopy(run)
    snapshot=frozen_snapshot(run,change_for(run))
    assert run==original
    assert snapshot['parameters']['answer_source']=='fixtures'
    assert snapshot['parameters']['judge_selection']=='configured'
    assert snapshot['dataset_snapshot']['cases'][0]['answers']=={'A':'Generated answer A','B':'Generated answer B'}
    assert len(snapshot['dataset_snapshot']['cases'])==1
    before=run['report']['versions']['settings_snapshot']
    after=snapshot['settings_snapshot']
    assert {k:v for k,v in before.items() if k!='rubric'}=={k:v for k,v in after.items() if k!='rubric'}
    assert snapshot['dataset_snapshot']['cases'][0]['evidence']==run['report']['rows'][0]['evidence']


def test_rejects_unchanged_and_incomplete_rubrics(tmp_path):
    run=baseline(Store(tmp_path/'test.db'))
    with pytest.raises(ValueError,match='Change at least'):
        frozen_snapshot(run,RubricChange(rubric=run['report']['versions']['settings_snapshot']['rubric']))
    with pytest.raises(ValueError):
        RubricChange(rubric={'faithfulness':{'0':'bad'}})


def test_api_queues_pinned_comparison_and_exposes_result(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    store=Store(tmp_path/'test.db');run=baseline(store)
    with TestClient(create_app(store,start_worker=False)) as client:
        assert client.get('/experiments/'+run['id']).status_code==200
        response=client.post('/api/runs/'+run['id']+'/rubric-comparisons',json=change_for(run).model_dump())
        assert response.status_code==202
        cid=response.json()['id'];child=store.run(cid)
        assert client.get('/api/runs/'+cid+'/rubric-result').status_code==409
        report=deepcopy(run['report']);report['comparison']=child['request']['comparison']
        report['rows'][0]['points']['A']['scores']['faithfulness']=1
        store.finish(cid,report=report)
        result=client.get('/api/runs/'+cid+'/rubric-result')
        assert result.status_code==200
        assert any(r['delta']!=0 for r in result.json()['scores'])
        assert store.run(run['id'])['report']==run['report']


def test_changed_answers_cannot_be_reported_as_rubric_effect(tmp_path):
    run=baseline(Store(tmp_path/'test.db'))
    candidate=deepcopy(run['report']);candidate['rows'][0]['answers']['A']='Different answer'
    with pytest.raises(ValueError,match='identical answers'):
        changes(run['report'],candidate)
