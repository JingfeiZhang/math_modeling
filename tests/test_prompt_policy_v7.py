from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from src.workflow.competition_workflow import initialize, prompt
from src.workflow.prompt_policy import assemble_packet, format_receipt, load_policy, validate_packet, validate_policy


ROOT = Path(__file__).resolve().parents[1]


def _fixture(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    shutil.copy2(ROOT / "config" / "workflow.yaml", root / "config" / "workflow.yaml")
    for relative in (
        "config/prompt_policy.yaml",
        "config/schemas/prompt_policy.schema.json",
        "config/schemas/prompt_packet.schema.json",
        "config/schemas/prompt_receipt.schema.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for source_dir in (ROOT / "templates" / "prompts" / "stages", ROOT / "templates" / "prompts" / "roles"):
        target_dir = root / source_dir.relative_to(ROOT)
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.glob("*.yaml"):
            shutil.copy2(source, target_dir / source.name)
    (root / "project.yaml").write_text(
        yaml.safe_dump({
            "schema_version": 1,
            "workflow_contract_version": 7,
            "prompt_policy_version": 1,
            "prompt_mode": "progress-first",
            "paper_prompt_mode": "external",
            "project_id": "fixture-v7",
            "profile_id": "cumcm",
        }, sort_keys=False),
        encoding="utf-8",
    )
    (root / "contest.yaml").write_text(
        yaml.safe_dump({"competition": "CUMCM", "problem": "C"}), encoding="utf-8"
    )
    question = root / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    question.parent.mkdir(parents=True)
    payload = yaml.safe_load((ROOT / "templates" / "workflow" / "question.yaml").read_text(encoding="utf-8"))
    payload["problem_id"] = "C"
    payload["question_id"] = "Q1"
    question.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_policy_and_contract_schemas_are_valid() -> None:
    policy = load_policy(ROOT)
    assert validate_policy(policy) == []
    for name, payload in (
        ("prompt_policy.schema.json", policy),
        ("prompt_receipt.schema.json", format_receipt()),
    ):
        schema = json.loads((ROOT / "config" / "schemas" / name).read_text(encoding="utf-8"))
        assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_yaml_packet_round_trips_through_validator(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", "Q1", ROOT)
    path = tmp_path / "packet.yaml"
    path.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False), encoding="utf-8")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert validate_packet(loaded) == []


def test_packet_rejects_wrong_project_identity(tmp_path: Path) -> None:
    _fixture(tmp_path)
    with pytest.raises(ValueError, match="project_id mismatch|selected project_id"):
        assemble_packet(tmp_path, "other-project", "P0", "orchestrator", None, ROOT)


def test_prompt_writes_only_verification_output(tmp_path: Path) -> None:
    _fixture(tmp_path)
    formal = {
        "state/decision_log.json": "{}",
        "results/C/claims.json": "{}",
        "paper/main.tex": "\\documentclass{article}",
        "paper/figure_contracts.yaml": "schema_version: 2\n",
        "output/release/release_manifest.json": "{}",
    }
    before = {}
    for relative, content in formal.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        before[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = prompt(tmp_path, "fixture-v7", "P0", "orchestrator", None, ROOT)
    assert result["status"] == "READY"
    for relative, digest in before.items():
        assert hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest() == digest
    assert (tmp_path / "output/_verification/prompts/P0/orchestrator/project/prompt_packet.yaml").is_file()


def test_synthetic_project_rehearses_p0_through_p6_prompt_routing(tmp_path: Path) -> None:
    _fixture(tmp_path)
    problem_file = tmp_path / "problems" / "incoming" / "problem-C.txt"
    problem_file.parent.mkdir(parents=True, exist_ok=True)
    problem_file.write_text("问题一 建立预测模型。\n问题二 根据预测结果优化方案。\n", encoding="utf-8")

    p0 = prompt(tmp_path, "fixture-v7", "P0", "orchestrator", None, ROOT)
    initialized = initialize(tmp_path, "C", problem_file, ROOT)
    assert initialized["questions"] == ["Q1", "Q2"]
    routes = [
        ("P1", "orchestrator", None),
        ("P2", "solver", "Q1"),
        ("P3a", "solver", "Q1"),
        ("P4", "paper", "Q1"),
        ("P5", "visualization", "Q1"),
        ("P6", "studio_release", "Q1"),
    ]
    reports = [p0, *(prompt(tmp_path, "fixture-v7", stage, role, question, ROOT) for stage, role, question in routes)]

    assert all(item["status"] == "READY" for item in reports)
    assert not (tmp_path / "submission").exists() or not any((tmp_path / "submission").rglob("prompt_*"))
    for stage, role, question in routes:
        packet = tmp_path / "output" / "_verification" / "prompts" / stage / role / (question or "project") / "prompt_packet.yaml"
        payload = yaml.safe_load(packet.read_text(encoding="utf-8"))
        assert payload["project_id"] == "fixture-v7"
        assert payload["question_id"] == (question or "")


def test_policy_rejects_blocking_deferred_overlap() -> None:
    policy = load_policy(ROOT)
    policy["stages"]["P2"]["deferred"].append(policy["stages"]["P2"]["blocking"][0])
    assert any("overlap" in item for item in validate_policy(policy))


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda value: value["authority_order"].reverse(), "authority_order"),
        (lambda value: value["stages"]["P2"].update({"gate": "G6"}), "gate"),
        (lambda value: value["roles"].update({"extra": value["roles"]["reviewer"]}), "roles"),
    ],
)
def test_policy_rejects_fixed_contract_drift(mutation, expected: str) -> None:
    policy = load_policy(ROOT)
    mutation(policy)
    assert any(expected in item for item in validate_policy(policy))


@pytest.mark.parametrize("stage,gate", [("P0", "G0"), ("P2", "G1"), ("P4", "G4"), ("P6", "G6")])
def test_packet_binds_stage_role_project_and_question(tmp_path: Path, stage: str, gate: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P0" else "Q1"
    packet = assemble_packet(tmp_path, "fixture-v7", stage, "solver", question, ROOT)
    assert packet["project_id"] == "fixture-v7"
    assert packet["gate"] == gate
    assert packet["question_id"] == (question or "")
    assert packet["input_contract"]
    assert packet["protected_paths"]
    assert all(item.startswith(("project:", "shared:")) for item in packet["context_refs"])
    assert validate_packet(packet) == []
    schema = json.loads((ROOT / "config" / "schemas" / "prompt_packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []


def test_p2_and_p3_defer_release_audits(tmp_path: Path) -> None:
    _fixture(tmp_path)
    for stage in ("P2", "P3a", "P3b"):
        packet = assemble_packet(tmp_path, "fixture-v7", stage, "solver", "Q1", ROOT)
        joined = " ".join(packet["deferred_conditions"])
        assert "PDF" in joined or "发布" in joined or "G5/G6" in joined
        assert "package" not in packet["allowed_actions"]


def test_p5_allows_paper_evidence_and_p6_restores_release_checks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    p5 = assemble_packet(tmp_path, "fixture-v7", "P5", "paper", "Q1", ROOT)
    p6 = assemble_packet(tmp_path, "fixture-v7", "P6", "studio_release", "Q1", ROOT)
    assert "paper-evidence" in p5["allowed_actions"]
    assert {"audit", "package", "seal", "verify-release"} <= set(p6["allowed_actions"])


def test_packet_rejects_invalid_scope_and_missing_question(tmp_path: Path) -> None:
    _fixture(tmp_path)
    with pytest.raises(ValueError, match="question_id"):
        assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", None, ROOT)
    packet = assemble_packet(tmp_path, "fixture-v7", "P2", "solver", "Q1", ROOT)
    packet["read_scope"].append("D:/outside")
    assert any("unsafe path" in item for item in validate_packet(packet))
    packet = assemble_packet(tmp_path, "fixture-v7", "P4", "solver", "Q1", ROOT)
    packet["question_id"] = ""
    assert any("requires question_id" in item for item in validate_packet(packet))


def test_compact_receipt_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="receipt status"):
        format_receipt({"status": "UNKNOWN"})


def test_compact_receipt_rejects_unhashed_evidence_and_routine_decision_requests() -> None:
    with pytest.raises(ValueError, match="path#sha256"):
        format_receipt({"evidence": ["results/output.json"]})
    with pytest.raises(ValueError, match="critical decision"):
        format_receipt({"decision_request": "是否改一下普通图例位置"})
