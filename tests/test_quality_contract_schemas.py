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


def test_semantics_supports_requirement_coverage_mapping() -> None:
    schema = load_schema("semantic_contract.schema.json")
    instance = load_template("semantic_contract.yaml")
    instance["requirement_coverage"] = [
        {
            "requirement_id": "req-cost",
            "source_locator": "problem p.2",
            "model_element": "objective.total_cost",
            "output_id": "answer",
            "metric_id": "primary",
            "constraint_ids": ["hard-1"],
            "scenario_ids": ["base"],
            "validation_method": "compare against the hand-calculated case",
            "paper_location": "Q1 results",
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/oracle.json",
            "status": "verified",
        }
    ]
    Draft202012Validator(schema).validate(instance)


def test_requirement_coverage_rejects_absolute_evidence_locator() -> None:
    schema = load_schema("semantic_contract.schema.json")
    instance = load_template("semantic_contract.yaml")
    instance["requirement_coverage"] = [
        {
            "requirement_id": "req-1",
            "source_locator": "problem p.1",
            "evidence_locator": "D:/outside/oracle.json",
        }
    ]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_metric_contract_carries_direction_and_denominator() -> None:
    schema = load_schema("metric_contract.schema.json")
    instance = load_template("metric_contract.yaml")
    metric = instance["metrics"][0]
    metric.pop("denominator")
    Draft202012Validator(schema).validate(instance)


def test_metric_contract_supports_validation_protocol() -> None:
    schema = load_schema("metric_contract.schema.json")
    instance = load_template("metric_contract.yaml")
    instance["validation_protocol"] = {
        "status": "VERIFIED",
        "applicable": True,
        "strategy": "rolling-origin",
        "split_unit": "day",
        "holdout_scope": "last 20 percent of observation windows",
        "leakage_checks": ["fit preprocessing on training windows only"],
        "primary_metric_ids": ["primary"],
        "uncertainty_outputs": ["prediction interval coverage"],
        "acceptance_criteria": [
            {
                "id": "beat-baseline",
                "metric_id": "primary",
                "comparator": "baseline",
                "operator": "less-than",
                "rationale": "the primary error must improve over the comparable baseline",
            }
        ],
        "evidence_locator": "experiments/DEMO/Q1/formal/run-1/validation.json",
    }
    Draft202012Validator(schema).validate(instance)


def test_metric_validation_protocol_supports_not_applicable_reason() -> None:
    schema = load_schema("metric_contract.schema.json")
    instance = load_template("metric_contract.yaml")
    instance["validation_protocol"] = {
        "status": "READY",
        "applicable": False,
        "not_applicable_reason": "the result is a deterministic identity",
        "strategy": "not-applicable",
        "acceptance_criteria": [],
    }
    Draft202012Validator(schema).validate(instance)


def test_metric_validation_protocol_rejects_absolute_evidence_locator() -> None:
    schema = load_schema("metric_contract.schema.json")
    instance = load_template("metric_contract.yaml")
    instance["validation_protocol"]["evidence_locator"] = "C:/outside/validation.json"
    with pytest.raises(ValidationError):
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


def test_algorithm_contract_supports_verification_closed_loop() -> None:
    schema = load_schema("algorithm_evidence.schema.json")
    instance = load_template("algorithm_evidence.yaml")
    instance["oracle_cases"] = [
        {
            "id": "tiny-enumeration",
            "applicable": True,
            "purpose": "verify the objective and constraints",
            "method": "enumeration",
            "input_locator": "experiments/DEMO/Q1/fixtures/tiny.json",
            "expected_result": "objective=12",
            "tolerance": 0,
            "passed": True,
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/oracle.json",
        }
    ]
    instance["invariants"] = [
        {
            "id": "capacity",
            "kind": "feasibility",
            "statement": "assigned load never exceeds capacity",
            "check_method": "assert every time-slot residual is nonnegative",
            "tolerance": 1e-9,
            "passed": True,
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/invariants.json",
        }
    ]
    instance["model_comparison"] = [
        {
            "id": "baseline-row",
            "model_id": "greedy-baseline",
            "role": "baseline",
            "comparable_output": True,
            "primary_metric": "primary",
            "metric_value": 15.2,
            "improvement": 0,
            "retained": False,
            "retained_reason": "reference only",
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/comparison.json",
        },
        {
            "id": "main-row",
            "model_id": "main-model",
            "role": "main",
            "comparable_output": True,
            "primary_metric": "primary",
            "metric_value": 12.0,
            "improvement": "21.1%",
            "retained": True,
            "retained_reason": "improves the primary metric while satisfying constraints",
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/comparison.json",
        },
    ]
    instance["robustness"] = [
        {
            "id": "demand-shock",
            "perturbation": "demand +/-10%",
            "metric": "primary",
            "result": "feasible in all tested scenarios",
            "boundary": "tested range only",
            "passed": True,
            "evidence_locator": "experiments/DEMO/Q1/formal/run-1/robustness.json",
        }
    ]
    Draft202012Validator(schema).validate(instance)


def test_algorithm_oracle_supports_reviewed_not_applicable_reason() -> None:
    schema = load_schema("algorithm_evidence.schema.json")
    instance = load_template("algorithm_evidence.yaml")
    instance["oracle_cases"] = [
        {
            "id": "analytical-oracle",
            "applicable": False,
            "not_applicable_reason": "no tractable analytical or exhaustive oracle exists",
        }
    ]
    Draft202012Validator(schema).validate(instance)


def test_algorithm_contract_supports_challenger_omission_reason() -> None:
    schema = load_schema("algorithm_evidence.schema.json")
    instance = load_template("algorithm_evidence.yaml")
    instance["challenger_not_applicable_reason"] = (
        "the exact baseline already exhausts the tractable candidate space"
    )
    instance["model_comparison"] = [
        {
            "id": "main-row",
            "model_id": "main-model",
            "role": "main",
            "comparable_output": True,
            "primary_metric": "primary",
        },
        {
            "id": "baseline-row",
            "model_id": "exact-baseline",
            "role": "baseline",
            "comparable_output": True,
            "primary_metric": "primary",
        },
    ]
    Draft202012Validator(schema).validate(instance)


@pytest.mark.parametrize("field", ["oracle_cases", "invariants", "model_comparison", "robustness"])
def test_algorithm_verification_rejects_absolute_evidence_locators(field: str) -> None:
    schema = load_schema("algorithm_evidence.schema.json")
    instance = load_template("algorithm_evidence.yaml")
    valid_items = {
        "oracle_cases": {
            "id": "o1",
            "applicable": True,
            "method": "analytical",
            "expected_result": "zero",
            "evidence_locator": "D:/outside/result.json",
        },
        "invariants": {
            "id": "i1",
            "kind": "boundary",
            "statement": "x >= 0",
            "check_method": "assert",
            "evidence_locator": "D:/outside/result.json",
        },
        "model_comparison": {
            "id": "m1",
            "model_id": "baseline",
            "role": "baseline",
            "comparable_output": True,
            "primary_metric": "primary",
            "evidence_locator": "D:/outside/result.json",
        },
        "robustness": {
            "id": "r1",
            "perturbation": "+10%",
            "metric": "primary",
            "result": "stable",
            "boundary": "tested range",
            "evidence_locator": "D:/outside/result.json",
        },
    }
    instance[field] = [valid_items[field]]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


@pytest.mark.parametrize(
    "schema_name, template_name, field",
    [
        ("semantic_contract.schema.json", "semantic_contract.yaml", "requirement_coverage"),
        ("metric_contract.schema.json", "metric_contract.yaml", "validation_protocol"),
        ("algorithm_evidence.schema.json", "algorithm_evidence.yaml", "oracle_cases"),
        ("algorithm_evidence.schema.json", "algorithm_evidence.yaml", "invariants"),
        ("algorithm_evidence.schema.json", "algorithm_evidence.yaml", "model_comparison"),
        ("algorithm_evidence.schema.json", "algorithm_evidence.yaml", "robustness"),
    ],
)
def test_quality_contract_extensions_remain_backward_compatible(
    schema_name: str, template_name: str, field: str
) -> None:
    schema = load_schema(schema_name)
    instance = load_template(template_name)
    instance.pop("verification_profile")
    instance.pop(field)
    Draft202012Validator(schema).validate(instance)


def test_abstract_contract_rejects_missing_question_coverage() -> None:
    schema = load_schema("abstract_contract.schema.json")
    instance = load_template("abstract_contract.yaml")
    instance["questions"] = []
    Draft202012Validator(schema).validate(instance)
