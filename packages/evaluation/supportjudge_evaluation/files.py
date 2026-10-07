import json
import os
from pathlib import Path

from .models import Dataset, Settings
from dotenv import load_dotenv

ROOT = Path(os.environ.get("SUPPORTJUDGE_ROOT", Path.cwd()))

load_dotenv(ROOT / ".env", override=False)

def load_dataset(name):
    path = ROOT / "data" / "evals" / f"{name}.json"
    return Dataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_settings(mode, configuration=None):
    filename = configuration + ".json" if configuration else "demo.json" if mode == "demo" else os.environ.get("SUPPORTJUDGE_CONFIG", "live.json")
    return Settings.model_validate_json((ROOT / "configs" / "judges" / filename).read_text(encoding="utf-8"))
