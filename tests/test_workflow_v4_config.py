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
    assert list(phases) == ["P0", "P1", "P2", "P3a", "P3b", "P4", "P5", "P6"]
    assert phases["P3b"]["window"][-1] == timing["model_lock_fraction"]
    assert phases["P6"]["window"][0] == timing["deep_release_audit_start_fraction"]
    assert phases["P6"]["internal_windows"]["blocking_fixes_only"] == [0.95, 1.00]


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

    assert policy["version"] == "progressive-v2"
    assert policy["default_mode"] == "progress-first"
    assert policy["semantics"]["blocking_scope"] == "current-transition-only"
    assert policy["semantics"]["warning_behavior"] == "record-and-continue"
    assert policy["semantics"]["local_invalidation_only"] is True
    assert policy["quickcheck"]["target_runtime_seconds"] == 60
    assert "input-output-contract-incomplete" in policy["quickcheck"]["warning"]
    assert "core-hard-constraints-unchecked-or-failing" in policy["quickcheck"]["warning"]
    assert "core-hard-constraints" not in policy["quickcheck"]["blocking"]
    assert policy["checkpoint"]["target_runtime_seconds"] == 120
    assert policy["early_gate_forbidden_actions"]["gates"] == ["G0", "G1", "G2", "G3", "G4"]
    assert {
        "pdf-render",
        "font-audit",
        "pdf-visual-audit",
        "package-audit",
        "release-integrity-audit",
    } < set(policy["early_gate_forbidden_actions"]["actions"])
    assert policy["final_deep_audit"]["gates"] == ["G5", "G6"]
    assert policy["final_deep_audit"]["starts_after_fraction"] == 0.85


def test_progressive_audit_profiles_match_experiment_lifecycle() -> None:
    config = load_config()
    policy = config["audit_policy"]
    profiles = policy["profiles"]

    assert config["experiment_lifecycle"]["audit_profile_by_level"] == {
        "scratch": "scratch-quickcheck",
        "candidate": "candidate-checkpoint",
        "formal": "formal-g3-g4",
        "paper-evidence": "formal-g3-g4",
    }
    assert policy["profile_selection"] == {
        "scratch": "scratch-quickcheck",
        "candidate": "candidate-checkpoint",
        "formal": "formal-g3-g4",
        "paper-evidence": "formal-g3-g4",
        "release": "release-g5-g6",
    }
    assert profiles["scratch-quickcheck"]["action"] == "quickcheck"
    assert profiles["candidate-checkpoint"]["action"] == "checkpoint"
    assert profiles["formal-g3-g4"]["actions"][:3] == ["validate-G3", "freeze", "validate-G4"]
    assert profiles["release-g5-g6"]["actions"][-3:] == ["package", "seal", "verify-release"]


def test_early_profiles_block_only_directional_or_promotion_errors() -> None:
    profiles = load_config()["audit_policy"]["profiles"]
    scratch = profiles["scratch-quickcheck"]
    candidate = profiles["candidate-checkpoint"]

    for directional_error in (
        "explicit-project-and-question-match",
        "required-inputs-readable",
        "runner-starts",
        "output-path-contained-in-run-directory",
    ):
        assert directional_error in scratch["blocking"]

    assert scratch["enforcement"] == "smoke-only"
    assert scratch["target_runtime_seconds"] == 60
    assert "input-output-contract-incomplete" in scratch["warning"]
    assert "core-hard-constraints-unchecked-or-failing" in scratch["warning"]

    for promotion_error in (
        "input-output-unit-contract",
        "output-conservation",
        "metric-definition",
        "comparable-output-baseline",
        "core-hard-constraints",
    ):
        assert promotion_error in candidate["blocking"]

    assert candidate["block_effect"] == "candidate-promotion-only"
    assert candidate["enforcement"] == "promotion-minimum"
    assert candidate["target_runtime_seconds"] == 120
    assert candidate["blocks_further_scratch"] is False
    assert scratch["blocks_other_questions"] is False
    assert candidate["blocks_other_questions"] is False


def test_expensive_completeness_is_deferred_until_its_owning_profile() -> None:
    policy = load_config()["audit_policy"]
    profiles = policy["profiles"]
    scratch_deferred = set(profiles["scratch-quickcheck"]["deferred"])
    candidate_deferred = set(profiles["candidate-checkpoint"]["deferred"])

    assert {
        "literature-completeness",
        "figure-brief-and-contract",
        "manuscript-completeness",
        "full-artifact-hashes",
        "deterministic-replays",
    } <= scratch_deferred
    assert {
        "literature-completeness",
        "approved-figure-brief",
        "manuscript-completeness",
        "full-artifact-hashes",
        "multiple-deterministic-replays",
    } <= candidate_deferred
    assert profiles["scratch-quickcheck"]["minimum_deterministic_replays"] == 0
    assert profiles["candidate-checkpoint"]["minimum_deterministic_replays"] == 0
    assert policy["checkpoint"]["multiple_replays_required"] is False
    assert policy["early_nonblocking_completeness"] == {
        "through_gate": "G4",
        "items": ["literature", "figure-design", "figure-render", "manuscript", "bibliography", "appendix", "page-layout"],
    }


def test_formal_and_release_profiles_restore_evidence_rigor_progressively() -> None:
    config = load_config()
    profiles = config["audit_policy"]["profiles"]
    formal = profiles["formal-g3-g4"]
    release = profiles["release-g5-g6"]

    assert formal["minimum_deterministic_replays"] == 1
    assert formal["enforcement"] == "strict"
    assert "one-independent-deterministic-replay" in formal["blocking"]["G3"]
    assert "formal-artifact-hashes" in formal["blocking"]["G4"]
    assert "approved-figure-brief" in formal["warning_through_g4"]
    assert formal["invalidation_scope"] == "affected-question-only"
    assert "literature-and-bibliography-handoff" in release["blocking"]["G5"]
    assert "pdf-visual-layout-and-fonts" in release["blocking"]["G6"]
    assert release["enforcement"] == "strict"
    assert release["rerun_policy"] == "no-new-rerun-unless-hash-drift-or-release-blocker"
    assert config["visualization_design"]["formal"]["approved_brief_required_at_gate"] == "G5"
    assert config["visualization_design"]["formal"]["missing_brief_behavior_through_g4"] == "warning"


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
