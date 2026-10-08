import argparse
import json
from pathlib import Path

from supportjudge_evaluation.engine import evaluate
from supportjudge_evaluation.files import load_dataset, load_settings
from supportjudge_evaluation.models import Request
from supportjudge_api.store import Store


def main():
    parser = argparse.ArgumentParser(description="Run SupportJudge evaluations or start its local application")
    parser.add_argument("command", choices=["serve", "evaluate"])
    parser.add_argument("--mode", choices=["live"], default="live")
    parser.add_argument("--dataset", default="support-v1")
    parser.add_argument("--answers", choices=["fixtures", "generate"], default="generate")
    parser.add_argument("--split", choices=["development", "heldout"], default="development")
    parser.add_argument("--output", default="reports/latest.json")
    parser.add_argument("--gate", action="store_true", help="Exit 1 if release checks fail")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--config", default=None, help="Named JSON settings under configs/judges, without extension")
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("supportjudge_api.api:app", host="127.0.0.1", port=args.port, workers=1)
        return
    request = Request(mode=args.mode, dataset=args.dataset, answer_source=args.answers, split=args.split, configuration=args.config)
    try:
        report = evaluate(load_dataset(args.dataset), load_settings(args.mode, args.config), request, Store())
    except Exception as exc:
        print(f"Evaluation failed: {type(exc).__name__}. No release approval issued.")
        raise SystemExit(2) from exc
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"report": str(path), "mode": report["mode"], "gate": report["gate"], "metrics": report["metrics"]}, indent=2))
    if args.gate and not report["gate"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
