from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"
TEMPLATE_ROOT = ROOT / "templates" / "workflow"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def test_v4_schemas_are_valid_draft_2020_12() -> None:
    for name in (
        "experiment.schema.json",
        "run_manifest.schema.json",
        "question.schema.json",
        "probe_receipt.schema.json",
        "paper_evidence.schema.json",
        "figure_data_manifest.schema.json",
        "visual_intent.schema.json",
        "figure_brief.schema.json",
    ):
        Draft202012Validator.check_schema(load_schema(name))


def test_v4_workflow_templates_validate() -> None:
    cases = (
        ("experiment.yaml", "experiment.schema.json"),
        ("paper_evidence.yaml", "experiment.schema.json"),
        ("question.yaml", "question.schema.json"),
    )
    for template_name, schema_name in cases:
        instance = yaml.safe_load((TEMPLATE_ROOT / template_name).read_text(encoding="utf-8"))
        Draft202012Validator(load_schema(schema_name)).validate(instance)


def test_question_profile_is_optional_and_task_conditional() -> None:
    instance = yaml.safe_load((TEMPLATE_ROOT / "question.yaml").read_text(encoding="utf-8"))
    instance["question_profile"] = {
        "task_types": ["optimization"],
        "feature_tags": ["integer_constraints"],
        "active_checks": ["problem_interface", "baseline_comparison"],
        "not_applicable_checks": ["prediction_delivery"],
        "status": "READY",
        "source": "manual_and_derived",
    }
    Draft202012Validator(load_schema("question.schema.json")).validate(instance)
