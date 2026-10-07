import json
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import ROOT, load_dataset, load_settings
from supportjudge_evaluation.models import Annotation, Request, digest
from supportjudge_api.store import Store
from supportjudge_api.rubric_comparison import RubricChange, frozen_snapshot, changes


def create_app(store=None, start_worker=True):
    store = store or Store()
    stopping = threading.Event()
    submission_lock = threading.Lock()

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
                if "comparison" in snapshot:
                    report["comparison"] = snapshot["comparison"]
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
                for p in sorted((ROOT / "data" / "evals").glob("*.json")) if p.stem != "demo"]

    @app.get("/api/experiments")
    def experiments():
        return store.experiments()

    @app.get("/api/models")
    def models():
        from supportjudge_api.model_selection import catalog
        try:
            return catalog()
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/model-roles")
    def model_roles():
        settings = load_settings("live")
        active = store.active()
        if active:
            from supportjudge_evaluation.models import Settings
            settings = Settings.model_validate(store.run(active["run_id"])["report"]["versions"]["settings_snapshot"])
        return {"generator_prompts": settings.answer_prompts,
                "generators": [{"id": m.id, "model": m.model} for m in settings.answer_models],
                "judges": [{"id": m.id, "model": m.model} for m in settings.judges]}

    @app.get("/api/runs")
    def runs():
        return store.runs()

    @app.post("/api/runs", status_code=202)
    def submit(request: Request):
        try:
            if request.mode != "live" or request.dataset == "demo":
                raise ValueError("Experiments require live models and a support dataset")
            dataset = load_dataset(request.dataset)
            if request.mode == "live" and request.configuration is None and store.active():
                from supportjudge_evaluation.models import Settings
                active_run = store.run(store.active()["run_id"])
                settings = Settings.model_validate(active_run["report"]["versions"]["settings_snapshot"])
            else:
                settings = load_settings(request.mode, request.configuration)
            if not any(c.split == request.split for c in dataset.cases):
                raise ValueError("Selected split has no cases")
            if request.case_id is not None and not any(c.id == request.case_id and c.split == request.split for c in dataset.cases):
                raise ValueError("Unknown case in selected split")
            if request.mode == "demo" and request.answer_source == "generate":
                raise ValueError("Demo mode requires fixtures")
            with submission_lock:
                if request.generator_prompts is not None:
                    settings = settings.model_copy(update={"answer_prompts": request.generator_prompts.model_dump()})
                if request.judge_selection != "configured" or request.generator_models or request.judge_models:
                    from supportjudge_api.model_selection import catalog, resolve
                    previous = store.latest_judges()
                    settings = resolve(settings, request, catalog(), previous)
                if any(j.model.startswith("demo-") for j in settings.judges):
                    raise ValueError("Live judges must identify real models")
                needed = settings.judges + (settings.answer_models if request.answer_source == "generate" else [])
                if any(not os.environ.get(m.key_env) for m in needed):
                    raise ValueError("Required provider keys are not configured")
                run_id = store.create_run({"parameters": request.model_dump(), "dataset_snapshot": dataset.model_dump(),
                                           "settings_snapshot": settings.model_dump()})
            return {"id": run_id, "state": "pending", "judges": [m.model for m in settings.judges], "generators": [m.model for m in settings.answer_models]}
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

    @app.post("/api/runs/{run_id}/rubric-comparisons", status_code=202)
    def compare_rubric(run_id: str, change: RubricChange):
        baseline = find(run_id)
        try:
            snapshot = frozen_snapshot(baseline, change)
            if any(not os.environ.get(m["key_env"]) for m in snapshot["settings_snapshot"]["judges"]):
                raise ValueError("Required judge provider keys are not configured")
            child = store.create_run(snapshot)
            return {"id": child, "baseline_id": run_id, "state": "pending"}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/runs/{run_id}/rubric-result")
    def rubric_result(run_id: str):
        candidate = find(run_id)
        if candidate["state"] != "completed":
            raise HTTPException(409, "Rubric comparison is not complete")
        report = candidate["report"]
        if "comparison" not in report:
            raise HTTPException(422, "This experiment is not a rubric comparison")
        baseline = find(report["comparison"]["baseline_id"])
        try:
            return changes(baseline["report"], report)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/runs/{run_id}/annotations")
    def annotations(run_id: str):
        find(run_id)
        return store.annotations(run_id)

    @app.post("/api/runs/{run_id}/annotations", status_code=201)
    def annotate(run_id: str, annotation: Annotation):
        run = find(run_id)
        if run["state"] != "completed" or annotation.case_id not in {r["case_id"] for r in run["report"]["rows"]}:
            raise HTTPException(422, "Annotate a case from a completed run")
        store.annotate(run_id, annotation.model_dump())
        return {"status": "recorded", "note": "Independent review and adjudication required before importing gold labels"}

    @app.get("/api/promotions")
    def promotions():
        return store.promotions()

    @app.get("/api/configuration/active")
    def active():
        return {"active": store.active()}

    @app.post("/api/configuration/activate/{promotion_id}")
    def activate(promotion_id: str):
        try:
            return {"active": store.activate(promotion_id), "note": "Next live submissions use this approved snapshot. Select an earlier promotion to roll back."}
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/observability")
    def observability():
        from collections import Counter
        from supportjudge_statistics.stats import percentile
        records = store.runs()
        completed = [store.run(r["id"])["report"] for r in records if r["state"] == "completed"]
        latencies = [r["elapsed_seconds"] for r in completed]
        traces = [t for r in completed for t in r["traces"]]
        recent = Counter(tag for r in completed[:5] for tag, count in r["category_counts"].items() for _ in range(count))
        previous = Counter(tag for r in completed[5:10] for tag, count in r["category_counts"].items() for _ in range(count))
        tags = set(recent) | set(previous)
        def shares(counts):
            return {tag: counts[tag] / sum(counts.values()) if counts else 0 for tag in tags}
        before, after = shares(previous), shares(recent)
        return {"runs": len(records), "states": dict(Counter(r["state"] for r in records)),
                "run_p50_seconds": percentile(latencies, .5), "run_p99_seconds": percentile(latencies, .99),
                "reported_tokens": sum(t.get("tokens", 0) for t in traces),
                "judge_disagreements": sum(len(r["disagreements"]) for r in completed),
                "demo_runs": sum(r["mode"] == "demo" for r in completed),
                "live_runs": sum(r["mode"] == "live" for r in completed),
                "category_shares_recent": after, "category_shares_previous": before,
                "category_shift_l1": sum(abs(after[t] - before[t]) for t in tags) if previous and recent else None,
                "note": "Last 100 runs; category shift compares two five-run windows, not a model-drift claim."}

    @app.get("/api/compare/{baseline_id}/{candidate_id}")
    def compare(baseline_id: str, candidate_id: str):
        baseline, candidate = find(baseline_id)["report"], find(candidate_id)["report"]
        if not baseline or not candidate:
            raise HTTPException(409, "Both runs must be complete")
        for field in ("dataset",):
            if baseline["versions"][field] != candidate["versions"][field]:
                raise HTTPException(409, "Compare runs using the same dataset snapshot")
        fields = ("mode", "answer_source", "dataset", "split", "case_id", "traffic")
        if any(baseline["versions"]["request"].get(f) != candidate["versions"]["request"].get(f) for f in fields):
            raise HTTPException(409, "Compare runs using identical selection and answer-source settings")
        left = {(r["case_id"], r["judge"]): r for r in baseline["rows"]}
        changes = []
        for row in candidate["rows"]:
            old = left.get((row["case_id"], row["judge"]))
            if old and old["answers"] == row["answers"]:
                changes.append({"case_id": row["case_id"], "judge": row["judge"],
                                "preference_before": old["preference"], "preference_after": row["preference"],
                                "changed": old["points"] != row["points"] or old["preference"] != row["preference"]})
        return {"baseline": baseline_id, "candidate": candidate_id, "examples": changes,
                "note": "Descriptive shadow comparison. No automatic promotion or causal claim."}

    @app.post("/api/runs/{run_id}/promote")
    def promote(run_id: str):
        run = find(run_id)
        report = run["report"]
        if not report or report["mode"] != "live" or not report["gate"]["passed"]:
            raise HTTPException(409, "Promotion requires a live run that passes calibration and release checks")
        store.promote(run_id, report["versions"]["settings"])
        return {"status": "approved", "note": "Recorded configuration approval. Deployment selection remains explicit."}

    static = ROOT / "apps" / "web"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/experiments")
    def experiments_page():
        return FileResponse(static / "experiments.html")

    @app.get("/judges-pair")
    def judges_pair_page():
        return FileResponse(static / "judges-pair.html")

    @app.get("/judge-comparison")
    def judge_comparison_page():
        return FileResponse(static / "judges.html")

    @app.get("/experiments/{run_id}")
    def experiment_page(run_id: str):
        find(run_id)
        return FileResponse(static / "experiment.html")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
