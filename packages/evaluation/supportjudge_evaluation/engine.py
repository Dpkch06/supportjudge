import json
import os
import subprocess
import time
from datetime import datetime, timezone

import httpx

from .models import Pair, Point, digest
from supportjudge_statistics.stats import summarize


class Provider:
    def __init__(self, mode, cache, settings_hash):
        self.mode, self.cache, self.settings_hash = mode, cache, settings_hash
        self.traces = []

    def call(self, config, instruction, payload, schema=None):
        key = digest({"mode": self.mode, "config": config.model_dump(), "instruction": instruction,
                      "payload": payload, "schema": schema.__name__ if schema else None, "settings": self.settings_hash})
        cached = self.cache.get(key)
        if cached:
            self.traces.append({**cached["trace"], "cache_hit": True, "latency_seconds": 0, "cost_usd": 0, "tokens": 0})
            return schema.model_validate(cached["value"]) if schema else cached["value"]
        start = time.perf_counter()
        if self.mode == "demo":
            if schema is Point:
                dangerous = any(x in payload["answer"].lower() for x in ("guarantee", "password", "always refundable", "90 days"))
                score = 0 if dangerous else 4
                value = {"scores": {k: score for k in ("faithfulness", "helpfulness", "safety", "format_adherence")},
                         "verdict": "reject" if dangerous else "accept", "reason": "Simulated keyword check, not an LLM judgment.",
                         "evidence_ids": [payload["evidence"][0]["id"]]}
            elif schema is Pair:
                def quality(text):
                    return not any(x in text.lower() for x in ("guarantee", "password", "always refundable", "90 days"))
                a, b = quality(payload["answers"]["A"]), quality(payload["answers"]["B"])
                preference = "tie" if a == b else "A" if a else "B"
                if config.model == "demo-position-sensitive":
                    preference = "A"
                value = {"preference": preference, "reason": "Simulated comparison, not an LLM judgment.",
                         "evidence_ids": [payload["evidence"][0]["id"]]}
            else:
                raise ValueError("Demo mode uses fixture answers only")
            trace = {"model": config.model, "latency_seconds": time.perf_counter() - start, "tokens": 0, "cost_usd": 0, "cache_hit": False}
        else:
            key_value = os.environ.get(config.key_env)
            if not key_value:
                raise ValueError(f"Set {config.key_env} locally before a live run")
            body = {"model": config.model, "messages": [{"role": "system", "content": instruction},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
            if schema:
                body["response_format"] = {"type": "json_object"}
                body["messages"][0]["content"] += " Return only JSON matching this schema: " + json.dumps(schema.model_json_schema())
            with httpx.Client(timeout=90, follow_redirects=False) as client:
                response = client.post(config.base_url.rstrip("/") + "/chat/completions", json=body,
                                       headers={"Authorization": f"Bearer {key_value}"})
                response.raise_for_status()
                raw = response.json()
            content = raw["choices"][0]["message"]["content"]
            if schema:
                lines = content.strip().splitlines()
                if len(lines) >= 3 and lines[0].strip().lower() in {"```json", "```"} and lines[-1].strip() == "```":
                    content = "\n".join(lines[1:-1])
                value = json.loads(content)
            else:
                value = content
            usage = raw.get("usage", {})
            cost = usage.get("cost")
            if cost is None and config.input_per_million is not None and config.output_per_million is not None:
                cost = (usage.get("prompt_tokens", 0) * config.input_per_million + usage.get("completion_tokens", 0) * config.output_per_million) / 1e6
            trace = {"model": raw.get("model", config.model), "latency_seconds": time.perf_counter() - start,
                     "tokens": usage.get("total_tokens", 0), "cost_usd": cost, "cache_hit": False}
        parsed = schema.model_validate(value) if schema else value
        if schema and not set(parsed.evidence_ids).issubset({e["id"] for e in payload["evidence"]}):
            raise ValueError("Judge cited unknown evidence")
        self.traces.append(trace)
        self.cache.put(key, {"value": value, "trace": trace})
        return parsed


def evaluate(dataset, settings, request, cache):
    started = time.perf_counter()
    if request.mode == "demo" and request.answer_source != "fixtures":
        raise ValueError("Demo mode cannot generate model answers")
    cases = [c for c in dataset.cases if c.split == request.split and (request.case_id is None or c.id == request.case_id)]
    if not cases:
        raise ValueError("Selected split has no cases")
    selected = dataset.model_copy(update={"cases": cases})
    provider = Provider(request.mode, cache, digest(settings.model_dump()))
    rows = []
    for case in cases:
        payload = {"question": case.question, "evidence": [e.model_dump() for e in case.evidence]}
        answers = dict(case.answers)
        if request.answer_source == "generate":
            answers = {name: provider.call(config, settings.answer_prompts[name], payload)
                       for name, config in zip(("A", "B"), settings.answer_models)}
        for config in settings.judges:
            if request.mode == "live" and config.model.startswith("demo-"):
                raise ValueError("Select live settings containing real model identifiers")
            points = {name: provider.call(config, settings.judge_instruction,
                      {**payload, "rubric": settings.rubric, "answer": text}, Point).model_dump() for name, text in answers.items()}
            forward = provider.call(config, settings.judge_instruction, {**payload, "rubric": settings.rubric, "answers": answers}, Pair)
            reverse = provider.call(config, settings.judge_instruction,
                                    {**payload, "rubric": settings.rubric, "answers": {"A": answers["B"], "B": answers["A"]}}, Pair)
            mapped = {"A": "B", "B": "A", "tie": "tie", "insufficient": "insufficient"}[reverse.preference]
            rows.append({"case_id": case.id, "question": case.question, "tags": case.tags, "evidence": payload["evidence"],
                         "answers": answers, "judge": config.id, "points": points, "forward": forward.model_dump(),
                         "reverse": reverse.model_dump(), "preference": forward.preference,
                         "order_consistent": mapped == forward.preference,
                         "labels": case.labels.model_dump() if request.answer_source == "fixtures" else {"status": "unreviewed"}})
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    return {"mode": request.mode, "answer_source": request.answer_source, "created": datetime.now(timezone.utc).isoformat(),
            "versions": {"dataset": digest(dataset.model_dump()), "settings": digest(settings.model_dump()), "commit": commit,
                         "request": request.model_dump(), "settings_snapshot": settings.model_dump(),
                         "implementation_hash": implementation_hash()},
            "dataset_name": dataset.name, "dataset_provenance": dataset.provenance, "rows": rows,
            **summarize(rows, selected, settings, request.mode, request.answer_source, provider.traces),
            "traces": provider.traces, "elapsed_seconds": round(time.perf_counter() - started, 4)}


def implementation_hash():
    from pathlib import Path
    from .files import ROOT
    files = []
    for directory in ("packages", "services", "infra", "apps/web"):
        files.extend(p for p in (ROOT / directory).rglob("*") if p.suffix in {".py", ".js", ".css", ".html"} and "__pycache__" not in p.parts)
    return digest({str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in sorted(files)})
