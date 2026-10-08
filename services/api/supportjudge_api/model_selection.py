import itertools
import threading
import time

import httpx

from supportjudge_evaluation.models import ModelConfig, Settings

AUTO_POOL = (
    "anthropic/claude-haiku-4.5", "deepseek/deepseek-chat-v3.1",
    "mistralai/mistral-small-3.2-24b-instruct", "google/gemini-2.5-flash",
    "openai/gpt-4.1-mini",
)
_cache = None
_expires = 0
_lock = threading.Lock()


def catalog():
    global _cache, _expires
    with _lock:
        if _cache is not None and time.monotonic() < _expires:
            return _cache
        try:
            response = httpx.get("https://openrouter.ai/api/v1/models", timeout=20)
            response.raise_for_status()
            raw = response.json()["data"]
            entries = []
            for m in raw:
                architecture = m.get("architecture", {})
                if "text" not in architecture.get("output_modalities", ["text"]):
                    continue
                if "text" not in architecture.get("input_modalities", ["text"]):
                    continue
                pricing = m.get("pricing", {})
                entries.append({"id": m["id"], "name": m.get("name", m["id"]),
                    "judge_supported": "response_format" in m.get("supported_parameters", []),
                    "input_per_million": float(pricing["prompt"])*1e6 if pricing.get("prompt") is not None else None,
                    "output_per_million": float(pricing["completion"])*1e6 if pricing.get("completion") is not None else None})
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("OpenRouter model catalog is unavailable. Try again shortly.") from exc
        _cache = sorted(entries, key=lambda m: m["name"].lower())
        _expires = time.monotonic() + 300
        return _cache


def resolve(settings, request, models, previous=()):
    lookup = {m["id"]: m for m in models}
    generators = request.generator_models or [m.model for m in settings.answer_models]
    if len(set(generators)) != 2:
        raise ValueError("Choose two different generator models")
    if any(mid not in lookup for mid in generators):
        raise ValueError("A selected generator is not in the current OpenRouter catalog")
    if request.judge_selection == "manual":
        if request.judge_models is None:
            raise ValueError("Choose two judge models")
        judges = request.judge_models
    elif request.judge_selection == "rotate":
        if request.judge_models is not None:
            raise ValueError("Automatic rotation cannot include manual judge choices")
        pool = [m for m in AUTO_POOL if m in lookup and lookup[m]["judge_supported"] and m not in generators]
        pairs = [pair for pair in itertools.combinations(pool, 2) if pair[0].split('/')[0] != pair[1].split('/')[0]]
        if len(pairs) < 2:
            raise ValueError("Not enough available independent judges to rotate. Choose judges manually.")
        old = next((i for i, pair in enumerate(pairs) if set(pair) == set(previous)), -1)
        judges = list(pairs[(old + 1) % len(pairs)])
    else:
        if request.judge_models is not None:
            raise ValueError("Select manual judge mode to set judge models")
        judges = [m.model for m in settings.judges]
    if len(set(judges)) != 2 or set(judges) & set(generators):
        raise ValueError("Choose two different judges, separate from both generators")
    if any(mid not in lookup or not lookup[mid]["judge_supported"] for mid in judges):
        raise ValueError("A selected judge does not advertise JSON output support")
    def config(mid):
        m = lookup[mid]
        return ModelConfig(id=mid, model=mid, base_url="https://openrouter.ai/api/v1", key_env="OPENROUTER_API_KEY",
                           input_per_million=m["input_per_million"], output_per_million=m["output_per_million"])
    data = settings.model_dump()
    data.update(answer_models=[config(m).model_dump() for m in generators], judges=[config(m).model_dump() for m in judges])
    return Settings.model_validate(data)
