from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import load_dataset, load_settings
from supportjudge_evaluation.models import Labels, Request
from supportjudge_api.store import Store


def test_ai_references_never_become_human_calibration(tmp_path):
    dataset=load_dataset('demo')
    dataset.cases[0].labels=Labels(status='ai_authored',verdicts={'A':'reject','B':'accept'},preference='B',rationale='AI reference')
    report=evaluate(dataset,load_settings('demo'),Request(case_id=dataset.cases[0].id),Store(tmp_path/'test.db'))
    assert len(report['rows'])==2
    assert all(c['human_labels']==0 and c['agreement'] is None for c in report['calibration'])
    assert all(c['reference_labels']==2 for c in report['provisional_reference'])
    assert not report['gate']['passed']
