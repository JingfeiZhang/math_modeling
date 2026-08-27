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


def test_shared_knowledge_policy_is_non_authoritative_and_safe() -> None:
    policy = load_policy(ROOT)
    knowledge = policy["shared_knowledge"]
    assert policy["authority_order"] == [
        "official_rules", "project_contest_profile", "prompt_policy", "question_manifest",
        "formal_evidence", "candidate_evidence", "scratch_evidence", "external_literature",
    ]
    assert knowledge["contest_evidence_eligible"] is False
    assert knowledge["phases"] == ["P1", "P2", "P3a", "P3b"]
    mutated = dict(policy)
    mutated["shared_knowledge"] = {**knowledge, "index": "D:/outside/index.md"}
    assert any("safe relative path" in item for item in validate_policy(mutated))
    mutated["shared_knowledge"] = {**knowledge, "contest_evidence_eligible": True}
    assert any("never be contest evidence" in item for item in validate_policy(mutated))


def test_statistics_guidance_policy_is_early_solver_only_and_non_authoritative() -> None:
    policy = load_policy(ROOT)
    guidance = policy["statistics_guidance"]
    assert guidance["phases"] == ["P1", "P2", "P3a", "P3b"]
    assert guidance["roles"] == ["solver"]
    assert guidance["contest_evidence_eligible"] is False
    assert guidance["missing_behavior"] == "warning"
    assert guidance["stage_routes"]["P1"] == ["data_profile", "relation_selection"]
    mutated = dict(policy)
    mutated["statistics_guidance"] = {**guidance, "index": "D:/outside/index.md"}
    assert any("statistics_guidance.index" in item for item in validate_policy(mutated))
    mutated["statistics_guidance"] = {**guidance, "contest_evidence_eligible": True}
    assert any("statistics_guidance" in item for item in validate_policy(mutated))


def test_algorithm_source_policy_is_solver_only_and_non_authoritative() -> None:
    policy = load_policy(ROOT)
    sources = policy["algorithm_sources"]
    assert sources["roles"] == ["solver"]
    assert sources["phases"] == ["P1", "P2", "P3a", "P3b"]
    assert sources["contest_evidence_eligible"] is False
    assert sources["quality_standard"] == "references/algorithm-sources/QUALITY_STANDARD.md"
    mutated = dict(policy)
    mutated["algorithm_sources"] = {**sources, "cards": "D:/outside/cards"}
    assert any("algorithm_sources.cards" in item for item in validate_policy(mutated))
    mutated["algorithm_sources"] = {**sources, "quality_standard": "D:/outside/QUALITY_STANDARD.md"}
    assert any("algorithm_sources.quality_standard" in item for item in validate_policy(mutated))


def test_academic_quality_policy_is_safe_non_evidence_and_role_bound() -> None:
    policy = load_policy(ROOT)
    quality = policy["academic_quality"]
    assert quality["phases"] == ["P1", "P2", "P3a", "P3b", "P4", "P5"]
    assert quality["roles"] == ["solver", "literature", "visualization", "paper", "reviewer"]
    assert quality["contest_evidence_eligible"] is False
    for role in quality["roles"]:
        assert quality["profile"] in policy["roles"][role]["read_scope"]
    mutated = dict(policy)
    mutated["academic_quality"] = {**quality, "profile": "D:/outside/academic.md"}
    assert any("academic_quality.profile" in item for item in validate_policy(mutated))
    mutated["academic_quality"] = {**quality, "contest_evidence_eligible": True}
    assert any("academic_quality must never be contest evidence" in item for item in validate_policy(mutated))


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


def test_packet_schema_rejects_stage_gate_drift(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P4", "paper", "Q1", ROOT)
    packet["gate"] = "G0"
    schema = json.loads((ROOT / "config" / "schemas" / "prompt_packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet))
    packet = assemble_packet(tmp_path, "fixture-v7", "P6", "studio_release", "Q1", ROOT)
    packet["role"] = "solver"
    assert list(Draft202012Validator(schema).iter_errors(packet))


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


@pytest.mark.parametrize("stage,gate,role", [("P0", "G0", "orchestrator"), ("P2", "G1", "solver"), ("P4", "G4", "paper"), ("P6", "G6", "studio_release")])
def test_packet_binds_stage_role_project_and_question(tmp_path: Path, stage: str, gate: str, role: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P0" else "Q1"
    packet = assemble_packet(tmp_path, "fixture-v7", stage, role, question, ROOT)
    assert packet["project_id"] == "fixture-v7"
    assert packet["gate"] == gate
    assert packet["gate_sequence"]
    assert packet["execution_semantics"]["blocking"] == "current-transition-only"
    assert "不阻断本问题继续建模" in packet["execution_semantics"]["note"]
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


def test_local_skill_packets_expose_v72_inputs_without_write_authority(tmp_path: Path) -> None:
    _fixture(tmp_path)
    literature = assemble_packet(tmp_path, "fixture-v7", "P3a", "literature", "Q1", ROOT)
    assert "requirement coverage gaps" in literature["input_contract"]
    assert "metric and algorithm verification gaps" in literature["input_contract"]
    assert any("contracts" in item for item in literature["protected_paths"])

    visualization = assemble_packet(tmp_path, "fixture-v7", "P5", "visualization", "Q1", ROOT)
    assert "model verification status" in visualization["input_contract"]
    assert "current quality contract hashes" in visualization["input_contract"]
    assert any("contracts" in item for item in visualization["protected_paths"])


@pytest.mark.parametrize("stage", ["P1", "P2", "P3a", "P3b"])
def test_shared_knowledge_is_injected_only_for_early_solver_stages(tmp_path: Path, stage: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P1" else "Q1"
    packet = assemble_packet(tmp_path, "fixture-v7", stage, "solver", question, ROOT)
    assert "shared:references/competition-knowledge/index.md" in packet["context_refs"]
    assert "references/competition-knowledge/index.md" in packet["read_scope"]
    assert packet["output_contract"]["shared_knowledge"]["contest_evidence_eligible"] is False
    assert "references/competition-knowledge/modules" in packet["read_scope"]
    assert "references/competition-knowledge/playbooks/index.md" in packet["read_scope"]
    assert "shared:references/competition-knowledge/modules" in packet["context_refs"]
    assert "shared:references/competition-knowledge/playbooks/index.md" in packet["context_refs"]


@pytest.mark.parametrize("stage", ["P1", "P2", "P3a", "P3b"])
def test_statistics_guidance_is_injected_for_early_solver_stages(tmp_path: Path, stage: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P1" else "Q1"
    packet = assemble_packet(tmp_path, "fixture-v7", stage, "solver", question, ROOT)
    guidance = packet["output_contract"]["statistics_guidance"]
    assert guidance["contest_evidence_eligible"] is False
    assert guidance["route_ids"]
    assert guidance["expected_outputs"]
    assert "references/competition-knowledge/modules/statistics" in packet["read_scope"]
    assert "shared:references/competition-knowledge/modules/statistics" in packet["context_refs"]
    assert "不属于学术文献" in guidance["usage"]
    assert validate_packet(packet) == []


def test_statistics_guidance_is_keyword_only_for_literature(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "literature", "Q1", ROOT)
    assert "statistics_guidance" not in packet["output_contract"]
    assert "references/competition-knowledge/modules/statistics" not in packet["read_scope"]
    assert "关键词" in " ".join(packet["warning_conditions"])


@pytest.mark.parametrize("stage", ["P1", "P2", "P3a", "P3b"])
def test_algorithm_sources_are_injected_only_for_early_solver_stages(tmp_path: Path, stage: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P1" else "Q1"
    packet = assemble_packet(tmp_path, "fixture-v7", stage, "solver", question, ROOT)
    assert "shared:references/algorithm-sources/index.md" in packet["context_refs"]
    assert "references/algorithm-sources/cards" in packet["read_scope"]
    assert packet["output_contract"]["algorithm_sources"]["contest_evidence_eligible"] is False
    assert "不执行外部代码" in packet["output_contract"]["algorithm_sources"]["usage"]


def test_literature_gets_keyword_only_non_evidence_notice(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "literature", "Q1", ROOT)
    assert "shared:references/competition-knowledge/index.md" in packet["context_refs"]
    assert "references/competition-knowledge/cards" not in packet["read_scope"]
    assert "references/competition-knowledge/modules" not in packet["read_scope"]
    assert "references/competition-knowledge/playbooks/index.md" not in packet["read_scope"]
    assert "shared:references/competition-knowledge/modules" not in packet["context_refs"]
    assert "不属于学术文献" in " ".join(packet["warning_conditions"])
    assert "检索关键词" in packet["output_contract"]["shared_knowledge"]["usage"]
    assert "algorithm_sources" not in packet["output_contract"]


def test_missing_shared_knowledge_index_is_warning_not_assembly_blocker(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", "Q1", tmp_path)
    assert "共享教材速查索引不可用" in " ".join(packet["assembly_warnings"])


@pytest.mark.parametrize("stage,role", [("P0", "solver"), ("P6", "solver"), ("P2", "studio_release")])
def test_packet_rejects_stage_role_cross_contamination(tmp_path: Path, stage: str, role: str) -> None:
    _fixture(tmp_path)
    question = None if stage == "P0" else "Q1"
    with pytest.raises(ValueError, match="not allowed"):
        assemble_packet(tmp_path, "fixture-v7", stage, role, question, ROOT)


@pytest.mark.parametrize("stage,role", [("P4", "solver"), ("P5", "literature"), ("P6", "studio_release")])
def test_formal_and_release_stages_do_not_load_shared_knowledge(tmp_path: Path, stage: str, role: str) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", stage, role, "Q1", ROOT)
    assert "shared:references/competition-knowledge/index.md" not in packet["context_refs"]
    assert "references/competition-knowledge/modules" not in packet["read_scope"]
    assert "references/competition-knowledge/playbooks/index.md" not in packet["read_scope"]
    assert "shared_knowledge" not in packet["output_contract"]
    assert "algorithm_sources" not in packet["output_contract"]
    assert "statistics_guidance" not in packet["output_contract"]


def test_statistics_guidance_missing_sources_are_warnings(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", "Q1", tmp_path)
    assert "statistics_guidance" in packet["output_contract"]
    assert any("统计指导" in warning for warning in packet["assembly_warnings"])


def test_p0_does_not_load_statistics_guidance(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P0", "orchestrator", None, ROOT)
    assert "statistics_guidance" not in packet["output_contract"]
    assert not any("统计指导" in item for item in packet["read_scope"])


def test_statistics_guidance_cannot_be_promoted_to_evidence(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", "Q1", ROOT)
    packet["output_contract"]["statistics_guidance"]["contest_evidence_eligible"] = True
    issues = validate_packet(packet)
    assert any("cannot be contest evidence" in item for item in issues)


def test_statistics_guidance_cannot_overlap_project_write_scope(tmp_path: Path) -> None:
    _fixture(tmp_path)
    packet = assemble_packet(tmp_path, "fixture-v7", "P3a", "solver", "Q1", ROOT)
    packet["write_scope"].append("references/competition-knowledge")
    issues = validate_packet(packet)
    assert any("must not overlap project write_scope" in item for item in issues)


def test_p5_allows_paper_evidence_and_p6_restores_release_checks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    p5 = assemble_packet(tmp_path, "fixture-v7", "P5", "paper", "Q1", ROOT)
    p6 = assemble_packet(tmp_path, "fixture-v7", "P6", "studio_release", "Q1", ROOT)
    assert "paper-evidence" in p5["allowed_actions"]
    assert p5["gate_sequence"] == ["G4"]
    assert p6["gate_sequence"] == ["G5", "G6"]
    assert {"audit", "package", "seal", "verify-release"} <= set(p6["allowed_actions"])
    p3b = assemble_packet(tmp_path, "fixture-v7", "P3b", "solver", "Q1", ROOT)
    assert "promote" not in p3b["allowed_actions"]
    assert "promotion-recommendation" in p3b["allowed_actions"]


def test_prompt_preview_has_markdown_summary_and_internal_receipt(tmp_path: Path) -> None:
    _fixture(tmp_path)
    result = prompt(tmp_path, "fixture-v7", "P0", "orchestrator", None, ROOT)
    assert result["markdown"].startswith("**已就绪**")
    assert "decision_request" not in result["markdown"]
    assert (tmp_path / result["receipt"]).is_file()


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
    assert format_receipt({"decision_request": "是否需要缩小结论边界"})["decision_request"]


def test_receipt_markdown_omits_empty_machine_sections() -> None:
    from src.workflow.prompt_policy import format_receipt_markdown

    rendered = format_receipt_markdown(format_receipt({"status": "READY", "objective": "完成提示包"}))
    assert "**已就绪**" in rendered
    assert "decision_request" not in rendered
    assert "**需要确认**" not in rendered
    assert "warnings" not in rendered


def test_receipt_markdown_shows_only_real_decision_requests() -> None:
    from src.workflow.prompt_policy import format_receipt_markdown

    rendered = format_receipt_markdown(format_receipt({"status": "BLOCK_TRANSITION", "decision_request": "请确认主模型或 fallback 的取舍"}))
    assert "**需要确认**：请确认主模型或 fallback 的取舍" in rendered
