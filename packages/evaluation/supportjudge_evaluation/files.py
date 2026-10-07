import json
import os
from pathlib import Path

from .models import Dataset, Settings

ROOT = Path(os.environ.get("SUPPORTJUDGE_ROOT", Path.cwd()))


def load_dataset(name):
    path = ROOT / "data" / "evals" / f"{name}.json"
    return Dataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_settings(mode):
    filename = "demo.json" if mode == "demo" else os.environ.get("SUPPORTJUDGE_CONFIG", "live.json")
    return Settings.model_validate_json((ROOT / "configs" / "judges" / filename).read_text(encoding="utf-8"))
