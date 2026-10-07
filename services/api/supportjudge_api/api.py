import hmac
import json
import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import ROOT, load_dataset, load_settings
from supportjudge_evaluation.models import Annotation, Request, digest
from supportjudge_api.store import Store


def require_team(x_team_token: str = Header(default="")):
    expected = os.environ.get("SUPPORTJUDGE_TEAM_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Set SUPPORTJUDGE_TEAM_TOKEN to enable team actions")
    if not hmac.compare_digest(x_team_token, expected):
        raise HTTPException(401, "Team token required")


def create_app(store=None, start_worker=True):
    store = store or Store()
    stopping = threading.Event()

    def worker():
        store.interrupt()
        while not stopping.is_set():
            job = store.claim()
            if not job:
                stopping.wait(.25)
                continue
            try:
                snapshot = json.loads(job["request"])
                from supportjudge_evaluation.models import Dataset, Settings
                report = evaluate(Dataset.model_validate(snapshot["dataset_snapshot"]),
                                  Settings.model_validate(snapshot["settings_snapshot"]),
                                  Request.model_validate(snapshot["parameters"]), store)
                store.finish(job["id"], report=report)
            except Exception as exc:
                # Provider response bodies may contain sensitive information.
                store.finish(job["id"], error=f"{type(exc).__name__}: Evaluation failed. Check configuration and provider availability; no release approval issued.")

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=worker, daemon=True)
        if start_worker:
            thread.start()
        yield
        stopping.set()
        if start_worker:
            thread.join(timeout=2)

    app = FastAPI(title="SupportJudge", version="0.1.0", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/datasets")
    def datasets():
        return [{"name": p.stem, "cases": len(load_dataset(p.stem).cases), "provenance": load_dataset(p.stem).provenance}
                for p in sorted((ROOT / "data" / "evals").glob("*.json"))]

    @app.get("/api/runs")
    def runs():
        return store.runs()

    @app.post("/api/runs", status_code=202, dependencies=[Depends(require_team)])
    def submit(request: Request):
        try:
            dataset = load_dataset(request.dataset)
            settings = load_settings(request.mode)
            if not any(c.split == request.split for c in dataset.cases):
                raise ValueError("Selected split has no cases")
            if request.mode == "demo" and request.answer_source == "generate":
                raise ValueError("Demo mode requires fixtures")
            if request.mode == "live":
                if any(j.model.startswith("demo-") for j in settings.judges):
                    raise ValueError("Live judges must identify real models")
                needed = settings.judges + (settings.answer_models if request.answer_source == "generate" else [])
                if any(not os.environ.get(m.key_env) for m in needed):
                    raise ValueError("Required provider keys are not configured")
            run_id = store.create_run({"parameters": request.model_dump(), "dataset_snapshot": dataset.model_dump(),
                                       "settings_snapshot": settings.model_dump()})
            return {"id": run_id, "state": "pending"}
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(422, str(exc)) from exc

    def find(run_id):
        value = store.run(run_id)
        if value is None:
            raise HTTPException(404, "Run not found")
        return value

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        value = find(run_id)
        # Reports contain fictional examples only. Never deploy real tickets here.
        value.pop("request")
        return value

    @app.get("/api/runs/{run_id}/annotations", dependencies=[Depends(require_team)])
    def annotations(run_id: str):
        find(run_id)
        return store.annotations(run_id)

    @app.post("/api/runs/{run_id}/annotations", status_code=201, dependencies=[Depends(require_team)])
    def annotate(run_id: str, annotation: Annotation):
        run = find(run_id)
        if run["state"] != "completed" or annotation.case_id not in {r["case_id"] for r in run["report"]["rows"]}:
            raise HTTPException(422, "Annotate a case from a completed run")
        store.annotate(run_id, annotation.model_dump())
        return {"status": "recorded", "note": "Independent review and adjudication required before importing gold labels"}

    @app.get("/api/promotions")
    def promotions():
        return store.promotions()

    @app.post("/api/runs/{run_id}/promote", dependencies=[Depends(require_team)])
    def promote(run_id: str):
        run = find(run_id)
        report = run["report"]
        if not report or report["mode"] != "live" or not report["gate"]["passed"]:
            raise HTTPException(409, "Promotion requires a live run that passes calibration and release checks")
        store.promote(run_id, report["versions"]["settings"])
        return {"status": "approved", "note": "Recorded configuration approval. Deployment selection remains explicit."}

    static = ROOT / "apps" / "web"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
