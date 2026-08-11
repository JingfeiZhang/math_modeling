from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "workflow.yaml"
README_PATH = ROOT / "README.md"


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_v4_timing_has_model_lock_and_release_buffer() -> None:
    timing = load_config()["competition_timing"]
    phases = timing["phases"]

    assert timing["progress_metric"] == "elapsed_fraction"
    assert timing["model_lock_fraction"] == 0.60
    assert timing["deep_release_audit_start_fraction"] == 0.85
    assert list(phases) == ["P0", "P1", "P2", "P3a", "P3b", "P4", "P5", "P6a", "P6b"]
    assert phases["P3b"]["window"][-1] == timing["model_lock_fraction"]
    assert phases["P6a"]["window"][0] == timing["deep_release_audit_start_fraction"]
    assert phases["P6b"]["objective"] == "blocking-fixes-only"


def test_v4_experiment_lifecycle_separates_formal_and_paper_evidence() -> None:
    lifecycle = load_config()["experiment_lifecycle"]

    assert lifecycle["levels"] == ["scratch", "candidate", "formal", "paper-evidence"]
    assert lifecycle["candidate"]["forbidden_gates"] == ["G3", "G4"]
    assert lifecycle["formal"]["gates"] == ["G3", "G4"]
    assert "frozen-claims" in lifecycle["formal"]["requirements"]
    assert lifecycle["paper-evidence"]["parent_required"] == "formal"
    assert lifecycle["paper-evidence"]["primary_model_mutation"] == "forbidden"
    assert lifecycle["paper-evidence"]["reopen_on_primary_drift"] is True
    assert set(lifecycle["paper-evidence"]["scopes"]) == {"diagnostic", "sensitivity", "mechanism", "figure_support"}


def test_v4_audit_policy_keeps_deep_checks_out_of_g0_through_g4() -> None:
    policy = load_config()["audit_policy"]

    assert policy["quickcheck"]["target_runtime_seconds"] == 180
    assert policy["early_gate_forbidden_actions"]["gates"] == ["G0", "G1", "G2", "G3", "G4"]
    assert set(policy["early_gate_forbidden_actions"]["actions"]) == {
        "pdf-render",
        "font-audit",
        "pdf-visual-audit",
        "package-audit",
        "release-integrity-audit",
    }
    assert policy["final_deep_audit"]["gates"] == ["G5", "G6"]
    assert policy["final_deep_audit"]["starts_after_fraction"] == 0.85


def test_removed_blanket_result_generation_ban_stays_removed() -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")

    assert "forbid_new_result_generation" not in raw


def test_v5_visualization_design_lifecycle_is_evidence_bound() -> None:
    design = load_config()["visualization_design"]

    assert design["owner_skill"] == "visualization-design"
    assert design["state_owner"] == "mathmodel-skill"
    assert design["lifecycle"] == [
        "DATA_READY",
        "INTENT_READY",
        "BRIEF_READY",
        "DESIGN_APPROVED",
        "RENDERED",
        "QA_PASSED",
        "CONTRACT_READY",
    ]
    assert design["stale_on_hash_drift"] is True
    assert design["scratch"] == {
        "maximum_stage": "INTENT_READY",
        "contest_evidence_eligible": False,
    }
    assert design["candidate"]["maximum_stage"] == "BRIEF_READY"
    assert design["formal"]["approved_brief_required_for_declared_figures"] is True
    assert design["formal"]["render_required_at_gate"] == "G5"
    assert design["paper_evidence"]["primary_drift_result"] == "REOPEN_REQUIRED"
    assert design["commands"] == [
        "figure-data",
        "figure-intent",
        "figure-brief",
        "figure-render",
        "figure-qa",
        "figure-promote",
    ]
    assert design["strict_g5_requires_handoff"] is True
    assert design["legacy_missing_handoff"] == "warning"
    assert design["root_only_action"] == "figure-promote"


def test_readme_documents_v4_shortest_path_and_whitelist_governance() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    section = text.split("## Competition-day workflow", 1)[1].split("## Local-first Python environments", 1)[0]

    for action in (
        "initialize",
        "quickcheck",
        "checkpoint",
        "promote",
        "paper-evidence",
        "layout-check",
        "audit",
        "package",
        "seal",
        "verify-release",
        "archive-work",
    ):
        assert action in section
    for phrase in ("P0--P6", "G0--G6", "REOPEN_REQUIRED", "src/submission/", "output/release/", "显式白名单"):
        assert phrase in section
