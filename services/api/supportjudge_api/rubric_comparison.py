from copy import deepcopy
from statistics import mean

from pydantic import Field, model_validator

from supportjudge_evaluation.models import Record, Dataset, Settings, Request, digest

DIMENSIONS = ("faithfulness", "helpfulness", "safety", "format_adherence")


class RubricChange(Record):
    rubric: dict[str, dict[str, str]]
    name: str = Field(default="Custom rubric", min_length=1, max_length=100)

    @model_validator(mode="after")
    def complete_scale(self):
        if set(self.rubric) != set(DIMENSIONS):
            raise ValueError("Provide all four rubric dimensions")
        for scale in self.rubric.values():
            if set(scale) != {str(i) for i in range(5)}:
                raise ValueError("Each dimension requires score descriptions from 0 to 4")
            if any(not text.strip() or len(text) > 2000 for text in scale.values()):
                raise ValueError("Score descriptions must contain 1 to 2000 characters")
        return self


def frozen_snapshot(baseline, change):
    report = baseline["report"]
    if baseline["state"] != "completed" or not report or report["mode"] != "live":
        raise ValueError("Choose a completed live experiment")
    settings = Settings.model_validate(report["versions"]["settings_snapshot"])
    if settings.rubric == change.rubric:
        raise ValueError("Change at least one score description before comparing")
    original = baseline["request"]
    dataset = Dataset.model_validate(original["dataset_snapshot"])
    answers = {}
    for row in report["rows"]:
        if row["case_id"] in answers and answers[row["case_id"]] != row["answers"]:
            raise ValueError("Baseline judges did not evaluate identical answers")
        answers[row["case_id"]] = row["answers"]
    cases = []
    for case in dataset.cases:
        if case.id in answers:
            item = case.model_dump()
            item.update(answers=deepcopy(answers[case.id]), labels={"status": "unreviewed"})
            cases.append(item)
    if not cases or len(cases) != len(answers):
        raise ValueError("Baseline answers cannot be matched to the saved dataset")
    frozen = Dataset.model_validate({**dataset.model_dump(), "cases": cases})
    settings = Settings.model_validate({**settings.model_dump(), "rubric": change.rubric})
    parameters = Request.model_validate(original["parameters"]).model_copy(update={
        "answer_source": "fixtures", "judge_selection": "configured", "judge_models": None,
        "generator_models": None, "configuration": None})
    return {"parameters": parameters.model_dump(), "dataset_snapshot": frozen.model_dump(),
            "settings_snapshot": settings.model_dump(), "comparison": {
                "baseline_id": baseline["id"], "name": change.name,
                "baseline_rubric": report["versions"]["settings_snapshot"]["rubric"],
                "answers_hash": digest(answers), "kind": "rubric"}}


def changes(baseline, candidate):
    left = {(r["case_id"], r["judge"]): r for r in baseline["rows"]}
    details = []
    for row in candidate["rows"]:
        before = left.get((row["case_id"], row["judge"]))
        if before is None or before["answers"] != row["answers"] or before["evidence"] != row["evidence"]:
            raise ValueError("Comparison requires identical answers, evidence and judges")
        details.append({"case_id": row["case_id"], "judge": row["judge"], "question": row["question"],
                        "before": before, "after": row,
                        "preference_changed": before["preference"] != row["preference"],
                        "score_deltas": {a: {d: row["points"][a]["scores"][d]-before["points"][a]["scores"][d]
                                             for d in DIMENSIONS} for a in ("A", "B")}})
    if len(details) != len(left):
        raise ValueError("Comparison is missing baseline judgments")
    scores = []
    for judge in sorted({r["judge"] for r in details}):
        group = [r for r in details if r["judge"] == judge]
        for answer in ("A", "B"):
            for dimension in DIMENSIONS:
                before = mean(r["before"]["points"][answer]["scores"][dimension] for r in group)
                after = mean(r["after"]["points"][answer]["scores"][dimension] for r in group)
                scores.append({"judge": judge, "answer": answer, "dimension": dimension,
                               "before": before, "after": after, "delta": after-before})
    rubric_changes = [{"dimension": d, "score": score, "before": baseline["versions"]["settings_snapshot"]["rubric"][d][score],
                       "after": text} for d, scale in candidate["versions"]["settings_snapshot"]["rubric"].items()
                      for score, text in scale.items() if text != baseline["versions"]["settings_snapshot"]["rubric"][d][score]]
    return {"scores": scores, "examples": details, "rubric_changes": rubric_changes,
            "preference_changes": sum(r["preference_changed"] for r in details),
            "judgments": len(details), "comparison": candidate["comparison"],
            "note": "Answers, evidence and judge models are fixed. A single rerun also includes model sampling variability."}
