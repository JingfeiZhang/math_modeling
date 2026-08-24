from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"
TEMPLATE_ROOT = ROOT / "templates" / "workflow"
CASES = (
    ("semantic_contract.schema.json", "semantic_contract.yaml"),
    ("metric_contract.schema.json", "metric_contract.yaml"),
    ("algorithm_evidence.schema.json", "algorithm_evidence.yaml"),
    ("abstract_contract.schema.json", "abstract_contract.yaml"),
)


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def load_template(name: str) -> dict:
    value = yaml.safe_load((TEMPLATE_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize("schema_name, template_name", CASES)
def test_quality_contract_schemas_and_templates_are_valid(
    schema_name: str, template_name: str
) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(load_template(template_name))


def test_contracts_reject_absolute_paths() -> None:
    for schema_name, template_name in CASES:
        schema = load_schema(schema_name)
        instance = load_template(template_name)
        key = "source_problem" if schema_name == "semantic_contract.schema.json" else "source_question_set" if schema_name == "abstract_contract.schema.json" else "source_question"
        instance[key]["path"] = "D:/outside/problem.txt"
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(instance)


def test_semantics_distinguishes_fixed_input_from_decision_input() -> None:
    schema = load_schema("semantic_contract.schema.json")
    instance = load_template("semantic_contract.yaml")
    instance["inputs"][0]["role"] = "decision"
    Draft202012Validator(schema).validate(instance)
    instance["inputs"][0]["role"] = "free"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_metric_contract_carries_direction_and_denominator() -> None:
    schema = load_schema("metric_contract.schema.json")
    instance = load_template("metric_contract.yaml")
    metric = instance["metrics"][0]
    metric.pop("denominator")
    Draft202012Validator(schema).validate(instance)


def test_algorithm_contract_limits_claim_scope_and_objective_modes() -> None:
    schema = load_schema("algorithm_evidence.schema.json")
    instance = load_template("algorithm_evidence.yaml")
    instance["objective_mode"] = "unknown-mode"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)
    instance = load_template("algorithm_evidence.yaml")
    instance["scope"]["coverage_mode"] = "local-window"
    instance["scope"]["window"] = "72h"
    Draft202012Validator(schema).validate(instance)


def test_abstract_contract_rejects_missing_question_coverage() -> None:
    schema = load_schema("abstract_contract.schema.json")
    instance = load_template("abstract_contract.yaml")
    instance["questions"] = []
    Draft202012Validator(schema).validate(instance)
