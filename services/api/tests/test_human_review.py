import json
import pytest
from fastapi.testclient import TestClient
from supportjudge_api.api import create_app
from supportjudge_api.store import Store
from supportjudge_api.human_review import order_for
from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import load_dataset,load_settings
from supportjudge_evaluation.models import Request


@pytest.fixture
def review_app(tmp_path):
    store=Store(tmp_path/'review.db');dataset=load_dataset('support-v1');settings=load_settings('demo')
    request=Request(dataset='support-v1',case_id=dataset.cases[0].id)
    report=evaluate(dataset,settings,request,store)
    for row in report['rows']:
        row['points']['A']['verdict']='accept';row['points']['B']['verdict']='reject';row['preference']='A'
    rid=store.create_run({'parameters':request.model_dump(),'dataset_snapshot':dataset.model_dump(),'settings_snapshot':settings.model_dump()})
    store.finish(rid,report=report)
    with TestClient(create_app(store,start_worker=False)) as client:
        yield client,rid,store


def submission(client,rid,reviewer):
    c=client.get(f'/api/human-review/{rid}/blind',params={'reviewer':reviewer}).json()['cases'][0]
    x,y=order_for(rid,c['case_id'],reviewer)
    verdicts={'A':'reject','B':'accept'}
    return {'reviewer':reviewer,'case_id':c['case_id'],'answers_hash':c['answers_hash'],'verdict_x':verdicts[x],'verdict_y':verdicts[y],
            'preference':'X' if x=='B' else 'Y','rationale':'Synthetic test review with policy evidence','independent':True}


def test_blind_payload_hides_judgments_and_labels(review_app):
    client,rid,_=review_app
    data=client.get(f'/api/human-review/{rid}/blind',params={'reviewer':'Alice'}).json()
    assert set(data)=={'cases','reviewed','total','rubric'}
    assert set(data['cases'][0])=={'case_id','question','evidence','answers_hash','answers'}
    assert set(data['cases'][0]['answers'])=={'X','Y'}
    assert 'demo-neutral' not in json.dumps(data)


def test_reviews_require_two_distinct_names_and_adjudication(review_app):
    client,rid,store=review_app;base=f'/api/human-review/{rid}'
    before=store.run(rid)['report']
    a=submission(client,rid,'Alice')
    assert client.post(base+'/reviews',json=a).status_code==201
    assert client.post(base+'/reviews',json={**a,'reviewer':' alice '}).status_code==409
    resolution={'adjudicator':'Charlie','case_id':a['case_id'],'verdict_a':'reject','verdict_b':'accept','preference':'B','rationale':'Synthetic adjudication'}
    assert client.post(base+'/adjudication',json=resolution).status_code==409
    assert client.get(base+'/metrics').json()['adjudicated_cases']==0
    assert client.post(base+'/reviews',json=submission(client,rid,'Bob')).status_code==201
    ready=client.get(base+'/adjudication').json()['cases'][0]
    assert all(r['verdicts']=={'A':'reject','B':'accept'} and r['preference']=='B' for r in ready['reviews'])
    assert client.post(base+'/adjudication',json=resolution).status_code==201
    assert client.post(base+'/adjudication',json=resolution).status_code==409
    result=client.get(base+'/metrics').json()
    assert result['adjudicated_cases']==1
    for judge in result['judges']:
        assert judge['verdicts']==2 and judge['agreement']==0
        assert judge['false_acceptance_rate']==1 and judge['false_rejection_rate']==1
        assert judge['preference_agreement']==0
    assert store.run(rid)['report']==before
    assert client.get(base+'/blind',params={'reviewer':'new reviewer'}).json()['cases']==[]


def test_hash_empty_identity_and_attestation_validation(review_app):
    client,rid,_=review_app;base=f'/api/human-review/{rid}'
    payload=submission(client,rid,'Alice')
    assert client.post(base+'/reviews',json={**payload,'answers_hash':'wrong'}).status_code==409
    for change in [{'reviewer':'   '},{'rationale':'  '},{'independent':False}]:
        assert client.post(base+'/reviews',json={**payload,**change}).status_code==422
    assert client.get(base+'/metrics').json()['judges'][0]['false_acceptance_rate'] is None


def test_review_persists_and_does_not_transfer_to_other_runs(review_app):
    client,rid,store=review_app
    assert client.post(f'/api/human-review/{rid}/reviews',json=submission(client,rid,'Alice')).status_code==201
    copy=store.create_run(store.run(rid)['request']);store.finish(copy,report=store.run(rid)['report'])
    assert client.get(f'/api/human-review/{copy}/blind',params={'reviewer':'Alice'}).json()['reviewed']==0
    with TestClient(create_app(Store(store.path),start_worker=False)) as restarted:
        data=restarted.get(f'/api/human-review/{rid}/blind',params={'reviewer':'Alice'}).json()
        assert data['reviewed']==1 and data['cases']==[]


def test_final_decision_does_not_require_another_username(review_app):
    client,rid,_=review_app
    base=f'/api/human-review/{rid}'
    first=submission(client,rid,'Alice')
    assert client.post(base+'/reviews',json=first).status_code==201
    assert client.post(base+'/reviews',json=submission(client,rid,'Bob')).status_code==201
    result=client.post(base+'/adjudication',json={'case_id':first['case_id'],'verdict_a':'reject','verdict_b':'accept','preference':'B','rationale':'Final test decision based on the saved reviews'})
    assert result.status_code==201
    metrics=client.get(base+'/metrics').json()
    assert metrics['adjudicated_cases']==1
    assert metrics['adjudications'][0]['adjudicator'] is None
    assert len(metrics['adjudications'][0]['review_ids'])==2
    assert {r['reviewer'] for r in metrics['reviews']}=={'Alice','Bob'}
