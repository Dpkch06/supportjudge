import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field, field_validator
from supportjudge_evaluation.models import Record, digest


class ReviewInput(Record):
    reviewer: str = Field(min_length=1,max_length=100)
    case_id: str
    answers_hash: str
    verdict_x: Literal["accept","reject"]
    verdict_y: Literal["accept","reject"]
    preference: Literal["X","Y","tie","insufficient"]
    rationale: str = Field(min_length=1,max_length=4000)
    independent: Literal[True]

    @field_validator("reviewer","rationale")
    @classmethod
    def trim(cls,value):
        value=value.strip()
        if not value: raise ValueError("Enter a nonempty value")
        return value


class Resolution(Record):
    adjudicator: str | None = Field(default=None,min_length=1,max_length=100)
    case_id: str
    verdict_a: Literal["accept","reject"]
    verdict_b: Literal["accept","reject"]
    preference: Literal["A","B","tie","insufficient"]
    rationale: str = Field(min_length=1,max_length=4000)

    @field_validator("adjudicator","rationale")
    @classmethod
    def trim(cls,value):
        if value is None: return None
        if not value.strip(): raise ValueError("Enter a nonempty value")
        return value.strip()


def cases_for(run):
    cases={}
    for row in run["report"]["rows"]:
        case={k:row[k] for k in ("case_id","question","answers","evidence")}
        case["answers_hash"]=digest(case)
        if row["case_id"] in cases and cases[row["case_id"]]!=case:
            raise ValueError("Judges did not evaluate identical answers")
        cases[row["case_id"]]=case
    return cases


def order_for(run_id,case_id,reviewer):
    return ("B","A") if int(digest([run_id,case_id,reviewer.strip().casefold()])[0],16)%2 else ("A","B")


def router(store):
    with store.connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS human_reviews(id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, reviewer TEXT, value TEXT, created TEXT, UNIQUE(run_id,case_id,reviewer));
        CREATE TABLE IF NOT EXISTS human_resolutions(id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, value TEXT, created TEXT, UNIQUE(run_id,case_id));
        """)
    api=APIRouter(prefix="/api/human-review")
    def source(run_id):
        run=store.run(run_id)
        if not run: raise HTTPException(404,"Experiment not found")
        if run['state']!='completed': raise HTTPException(409,"Choose a completed experiment")
        try: return run,cases_for(run)
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    def values(table,run_id):
        with store.connection() as db:
            return [json.loads(r[0]) for r in db.execute(f"SELECT value FROM {table} WHERE run_id=? ORDER BY created",(run_id,))]

    @api.get('/{run_id}/blind')
    def blind(run_id:str,reviewer:str):
        if not reviewer.strip(): raise HTTPException(422,"Enter your reviewer name")
        run,cases=source(run_id)
        reviewed={r['case_id'] for r in values('human_reviews',run_id) if r['reviewer_key']==reviewer.strip().casefold()}
        resolved={r['case_id'] for r in values('human_resolutions',run_id)}
        pending=[]
        for case in cases.values():
            if case['case_id'] in reviewed or case['case_id'] in resolved: continue
            x,y=order_for(run_id,case['case_id'],reviewer)
            pending.append({k:case[k] for k in ('case_id','question','evidence','answers_hash')}|{'answers':{'X':case['answers'][x],'Y':case['answers'][y]}})
        return {'cases':pending,'reviewed':len(reviewed),'total':len(cases),'rubric':run['report']['versions']['settings_snapshot']['rubric']}

    @api.post('/{run_id}/reviews',status_code=201)
    def save_review(run_id:str,review:ReviewInput):
        _,cases=source(run_id)
        case=cases.get(review.case_id)
        if not case or case['answers_hash']!=review.answers_hash: raise HTTPException(409,"Answers changed or case is unknown; reload the review")
        x,y=order_for(run_id,review.case_id,review.reviewer)
        record={'id':uuid.uuid4().hex,'case_id':review.case_id,'reviewer':review.reviewer,'reviewer_key':review.reviewer.casefold(),
                'answers_hash':case['answers_hash'],'verdicts':{x:review.verdict_x,y:review.verdict_y},
                'preference':{'X':x,'Y':y}.get(review.preference,review.preference),'rationale':review.rationale,'independent':True}
        with store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM human_reviews WHERE run_id=? AND case_id=? AND reviewer=?',(run_id,review.case_id,record['reviewer_key'])).fetchone():
                raise HTTPException(409,"Your review is already saved; it cannot be overwritten")
            if db.execute('SELECT 1 FROM human_resolutions WHERE run_id=? AND case_id=?',(run_id,review.case_id)).fetchone():
                raise HTTPException(409,"This question is already adjudicated")
            db.execute('INSERT INTO human_reviews VALUES (?,?,?,?,?,?)',(record['id'],run_id,review.case_id,record['reviewer_key'],json.dumps(record),datetime.now(timezone.utc).isoformat()))
        return {'status':'saved'}

    @api.get('/{run_id}/adjudication')
    def adjudication(run_id:str):
        _,cases=source(run_id)
        reviews=values('human_reviews',run_id);resolved={r['case_id'] for r in values('human_resolutions',run_id)}
        eligible=[]
        for cid,case in cases.items():
            group=[r for r in reviews if r['case_id']==cid]
            if len(group)>=2 and cid not in resolved: eligible.append({**case,'reviews':group})
        return {'cases':eligible,'resolved':len(resolved),'awaiting_second_review':sum(sum(r['case_id']==cid for r in reviews)<2 for cid in cases if cid not in resolved)}

    @api.post('/{run_id}/adjudication',status_code=201)
    def resolve(run_id:str,resolution:Resolution):
        _,cases=source(run_id)
        case=cases.get(resolution.case_id)
        if not case: raise HTTPException(404,"Question not found")
        with store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            reviews=[json.loads(r[0]) for r in db.execute('SELECT value FROM human_reviews WHERE run_id=? AND case_id=?',(run_id,resolution.case_id))]
            if len({r['reviewer_key'] for r in reviews})<2: raise HTTPException(409,"Two independent reviewer names are required")
            if any(r['answers_hash']!=case['answers_hash'] for r in reviews): raise HTTPException(409,"Reviews refer to different answers")
            if db.execute('SELECT 1 FROM human_resolutions WHERE run_id=? AND case_id=?',(run_id,resolution.case_id)).fetchone(): raise HTTPException(409,"This adjudication is already saved")
            record={'id':uuid.uuid4().hex,'case_id':resolution.case_id,'adjudicator':resolution.adjudicator,
                    'verdicts':{'A':resolution.verdict_a,'B':resolution.verdict_b},'preference':resolution.preference,
                    'rationale':resolution.rationale,'answers_hash':case['answers_hash'],'review_ids':[r['id'] for r in reviews]}
            db.execute('INSERT INTO human_resolutions VALUES (?,?,?,?,?)',(record['id'],run_id,resolution.case_id,json.dumps(record),datetime.now(timezone.utc).isoformat()))
        return {'status':'adjudicated'}

    @api.get('/{run_id}/metrics')
    def metrics(run_id:str):
        run,cases=source(run_id)
        gold={r['case_id']:r for r in values('human_resolutions',run_id) if r['case_id'] in cases and r['answers_hash']==cases[r['case_id']]['answers_hash']}
        result=[]
        for judge in sorted({r['judge'] for r in run['report']['rows']}):
            rows=[r for r in run['report']['rows'] if r['judge']==judge and r['case_id'] in gold]
            judgments=[(r['points'][a]['verdict'],gold[r['case_id']]['verdicts'][a]) for r in rows for a in ('A','B')]
            bad=sum(g=='reject' for _,g in judgments);good=sum(g=='accept' for _,g in judgments)
            false_accept=sum(p=='accept' and g=='reject' for p,g in judgments);false_reject=sum(p=='reject' and g=='accept' for p,g in judgments)
            result.append({'judge':judge,'cases':len(rows),'verdicts':len(judgments),'agreement':sum(p==g for p,g in judgments)/len(judgments) if judgments else None,
                           'unacceptable_references':bad,'acceptable_references':good,'false_acceptances':false_accept,'false_rejections':false_reject,
                           'false_acceptance_rate':false_accept/bad if bad else None,'false_rejection_rate':false_reject/good if good else None,
                           'abstentions':sum(p=='insufficient' for p,_ in judgments),
                           'preference_agreement':sum(r['preference']==gold[r['case_id']]['preference'] for r in rows)/len(rows) if rows else None})
        return {'total_cases':len(cases),'adjudicated_cases':len(gold),'judges':result,'reviews':values('human_reviews',run_id),'adjudications':list(gold.values()),
                'note':'Human-entered reviews with self-declared identities. Metrics cover adjudicated cases only; existing experiment reports and release decisions are unchanged.'}
    return api
