import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(Record):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=15000)
    url: str
    retrieved: str
    provenance: str


class Labels(Record):
    status: Literal["unreviewed", "ai_authored", "human_reviewed"] = "unreviewed"
    reviewers: list[str] = []
    verdicts: dict[str, Literal["accept", "reject"]] = {}
    preference: Literal["A", "B", "tie", "insufficient"] | None = None
    rationale: str = ""

    @model_validator(mode="after")
    def independent(self):
        if self.status == "human_reviewed" and (len(set(self.reviewers)) < 2 or not self.rationale):
            raise ValueError("Human labels require two distinct reviewers and a rationale")
        return self


class Case(Record):
    id: str
    question: str = Field(min_length=1, max_length=10000)
    tags: list[str]
    split: Literal["development", "heldout"] = "development"
    evidence: list[Evidence] = Field(min_length=1)
    answers: dict[str, str]
    labels: Labels = Field(default_factory=Labels)

    @model_validator(mode="after")
    def answers_present(self):
        if set(self.answers) != {"A", "B"} or not all(self.answers.values()):
            raise ValueError("Provide exactly two nonempty fixture answers, A and B")
        if not set(self.labels.verdicts).issubset({"A", "B"}):
            raise ValueError("Unknown labeled answer")
        if len({e.id for e in self.evidence}) != len(self.evidence):
            raise ValueError("Evidence IDs must be unique within a case")
        return self


class Dataset(Record):
    name: str
    provenance: str
    cases: list[Case] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Case IDs must be unique")
        return self


class Scores(Record):
    faithfulness: int = Field(ge=0, le=4, strict=True)
    helpfulness: int = Field(ge=0, le=4, strict=True)
    safety: int = Field(ge=0, le=4, strict=True)
    format_adherence: int = Field(ge=0, le=4, strict=True)


class Point(Record):
    scores: Scores
    verdict: Literal["accept", "reject", "insufficient"]
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class Pair(Record):
    preference: Literal["A", "B", "tie", "insufficient"]
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class ModelConfig(Record):
    id: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    key_env: str = "OPENAI_API_KEY"
    input_per_million: float | None = Field(default=None, ge=0)
    output_per_million: float | None = Field(default=None, ge=0)


class Settings(Record):
    version: str
    judge_instruction: str
    rubric: dict[str, dict[str, str]]
    judges: list[ModelConfig] = Field(min_length=2, max_length=4)
    answer_models: list[ModelConfig] = Field(min_length=2, max_length=2)
    answer_prompts: dict[str, str]
    minimum_human_labels: int = Field(default=10, ge=1)
    minimum_agreement: float = Field(default=.85, ge=0, le=1)
    maximum_false_acceptance: float = Field(default=.1, ge=0, le=1)

    @model_validator(mode="after")
    def distinct(self):
        if len({j.id for j in self.judges}) != len(self.judges):
            raise ValueError("Judge IDs must be unique")
        if len({(j.base_url, j.model) for j in self.judges}) != len(self.judges):
            raise ValueError("Select distinct judge models")
        if set(self.answer_prompts) != {"A", "B"}:
            raise ValueError("Answer prompts require A and B")
        return self


class Request(Record):
    mode: Literal["demo", "live"] = "demo"
    answer_source: Literal["fixtures", "generate"] = "fixtures"
    dataset: str = Field(default="demo", pattern=r"^[a-zA-Z0-9_-]+$")
    split: Literal["development", "heldout"] = "development"
    generator_models: list[str] | None = Field(default=None, min_length=2, max_length=2)
    judge_models: list[str] | None = Field(default=None, min_length=2, max_length=2)
    judge_selection: Literal["configured", "rotate", "manual"] = "configured"
    case_id: str | None = None
    traffic: Literal["offline", "simulated_online"] = "offline"
    configuration: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]+$")


class Annotation(Record):
    case_id: str
    reviewer: str = Field(min_length=1, max_length=100)
    verdicts: dict[str, Literal["accept", "reject"]]
    preference: Literal["A", "B", "tie", "insufficient"]
    rationale: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def two(self):
        if set(self.verdicts) != {"A", "B"}:
            raise ValueError("Label both answers")
        return self
