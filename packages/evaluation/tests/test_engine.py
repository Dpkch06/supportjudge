import json

import pytest
from supportjudge_evaluation.engine import Provider, evaluate
from supportjudge_evaluation.files import load_dataset, load_settings
from supportjudge_evaluation.models import Labels, Point, Request
from supportjudge_api.store import Store


def test_demo_reports_order_bias_and_never_approves(tmp_path):
    report = evaluate(load_dataset('demo'), load_settings('demo'), Request(), Store(tmp_path/'test.db'))
    assert len(report['rows']) == 12
    assert not report['gate']['passed']
    assert len(report['disagreements']) == 6
    assert all(c['human_labels'] == 0 and c['agreement'] is None for c in report['calibration'])
    assert all(r['order_consistent'] for r in report['rows'] if r['judge'] == 'demo-neutral')
    assert not any(r['order_consistent'] for r in report['rows'] if r['judge'] == 'demo-position')


def test_cached_calls_do_not_rebill(tmp_path):
    store=Store(tmp_path/'test.db')
    args=load_dataset('demo'),load_settings('demo'),Request(),store
    evaluate(*args)
    report=evaluate(*args)
    assert report['metrics']['cache_hits'] == 48
    assert report['metrics']['cost_usd'] == 0


def test_human_labels_need_independent_reviewers():
    with pytest.raises(ValueError):
        Labels(status='human_reviewed',reviewers=['same','same'],rationale='test')


def test_missing_key_blocks_live_call(tmp_path, monkeypatch):
    settings=load_settings('demo')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError,match='OPENAI_API_KEY'):
        Provider('live',Store(tmp_path/'test.db'),'test').call(settings.judges[0],'test',{},Point)


def test_unknown_evidence_rejected(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY','test-not-real')
    value={'scores':dict(faithfulness=4,helpfulness=4,safety=4,format_adherence=4),'verdict':'accept','reason':'test','evidence_ids':['unknown']}
    def post(self,url,**kwargs):
        return httpx.Response(200,request=httpx.Request('POST',url),json={'choices':[{'message':{'content':json.dumps(value)}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    with pytest.raises(ValueError,match='unknown evidence'):
        Provider('live',Store(tmp_path/'test.db'),'test').call(load_settings('demo').judges[0],'test',{'evidence':[{'id':'known'}]},Point)


def test_provider_json_fence_is_parsed_but_extra_prose_is_rejected(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    value={'scores':dict(faithfulness=4,helpfulness=4,safety=4,format_adherence=4),'verdict':'accept','reason':'Supported','evidence_ids':['known']}
    content='```json\n'+json.dumps(value)+'\n```'
    def post(self,url,**kwargs):
        return httpx.Response(200,request=httpx.Request('POST',url),json={'choices':[{'message':{'content':content}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    config=load_settings('demo').judges[0]
    provider=Provider('live',Store(tmp_path/'test.db'),'test')
    assert provider.call(config,'test',{'evidence':[{'id':'known'}]},Point).verdict=='accept'
    content='Here is my answer: '+json.dumps(value)
    with pytest.raises(json.JSONDecodeError):
        provider.call(config,'changed',{'evidence':[{'id':'known'}]},Point)
