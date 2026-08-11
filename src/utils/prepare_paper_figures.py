#!/usr/bin/env python3
"""Collect paper figures from Figure Contracts without inventing data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ENHANCED_FIELDS = (
    "core_message", "visual_hierarchy", "target_size_profile", "statistics_report",
    "data_integrity", "label_strategy", "rasterized_layers", "palette_id", "color_encoding",
)


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_handoff_file(
    root: Path,
    handoff: dict[str, Any],
    path_field: str,
    hash_field: str,
) -> tuple[Path | None, str | None]:
    value = handoff.get(path_field)
    expected_hash = handoff.get(hash_field)
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None, f"{path_field} must be a non-empty project-relative path"
    path = (root / value).resolve()
    if not inside(root, path):
        return None, f"{path_field} escapes the project root"
    if not path.is_file():
        return None, f"{path_field} does not exist: {value}"
    if not isinstance(expected_hash, str) or expected_hash != sha256(path):
        return None, f"{path_field} hash is missing or stale"
    return path, None


def validate_design_handoff(root: Path, contract: dict[str, Any]) -> str | None:
    handoff = contract.get("design_handoff")
    if handoff is None:
        return None
    if not isinstance(handoff, dict):
        return "design_handoff must be an object"
    if handoff.get("design_status") != "APPROVED":
        return "design_handoff.design_status must be APPROVED"

    resolved: dict[str, Path] = {}
    for path_field, hash_field in (
        ("data_manifest", "data_manifest_sha256"),
        ("visual_intent", "visual_intent_sha256"),
        ("figure_brief", "figure_brief_sha256"),
        ("render_qa", "render_qa_sha256"),
    ):
        path, error = resolve_handoff_file(root, handoff, path_field, hash_field)
        if error:
            return error
        assert path is not None
        resolved[path_field] = path

    data_manifest = load_yaml(resolved["data_manifest"])
    visual_intent = load_yaml(resolved["visual_intent"])
    figure_brief = load_yaml(resolved["figure_brief"])
    try:
        render_qa = json.loads(resolved["render_qa"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"render_qa is not valid JSON: {exc}"

    if data_manifest.get("status") != "DATA_READY" or data_manifest.get("contest_evidence_eligible") is not True:
        return "data manifest is not eligible formal evidence"
    if visual_intent.get("status") != "READY" or visual_intent.get("contest_evidence_eligible") is not True:
        return "visual intent is not current formal evidence"
    if figure_brief.get("status") not in {"QA_PASSED", "CONTRACT_READY"} or figure_brief.get("contest_evidence_eligible") is not True:
        return "figure brief is not QA-passed formal evidence"
    if figure_brief.get("source_data_manifest_sha256") != sha256(resolved["data_manifest"]):
        return "figure brief references a stale data manifest"
    if figure_brief.get("visual_intent_sha256") != sha256(resolved["visual_intent"]):
        return "figure brief references a stale visual intent"
    if render_qa.get("passed") is not True or render_qa.get("status") != "QA_PASSED":
        return "render QA did not pass"
    if render_qa.get("brief_sha256") != sha256(resolved["figure_brief"]):
        return "render QA references a stale figure brief"
    if render_qa.get("data_manifest_sha256") != sha256(resolved["data_manifest"]):
        return "render QA references a stale data manifest"
    if render_qa.get("visual_intent_sha256") != sha256(resolved["visual_intent"]):
        return "render QA references a stale visual intent"

    _, error = resolve_handoff_file(
        root,
        {
            "path": data_manifest.get("source_run_manifest"),
            "hash": data_manifest.get("source_run_manifest_sha256"),
        },
        "path",
        "hash",
    )
    if error:
        return f"source run manifest is stale: {error}"
    for index, item in enumerate(data_manifest.get("source_artifacts", [])):
        if not isinstance(item, dict):
            return f"source_artifacts[{index}] is invalid"
        _, error = resolve_handoff_file(root, {"path": item.get("path"), "hash": item.get("sha256")}, "path", "hash")
        if error:
            return f"source_artifacts[{index}] is stale: {error}"
    _, error = resolve_handoff_file(
        root,
        {"path": figure_brief.get("source_script"), "hash": figure_brief.get("source_script_sha256")},
        "path",
        "hash",
    )
    if error:
        return f"figure source script is stale: {error}"
    for index, item in enumerate(figure_brief.get("data_integrity", {}).get("source_hashes", [])):
        if not isinstance(item, dict):
            return f"data_integrity.source_hashes[{index}] is invalid"
        _, error = resolve_handoff_file(root, {"path": item.get("path"), "hash": item.get("sha256")}, "path", "hash")
        if error:
            return f"data_integrity.source_hashes[{index}] is stale: {error}"

    qa_hashes = {
        str(item.get("sha256"))
        for item in render_qa.get("outputs", [])
        if isinstance(item, dict) and item.get("sha256")
    }
    for key in ("pdf", "svg", "png"):
        value = contract.get("outputs", {}).get(key)
        if not isinstance(value, str):
            return f"contract output {key} is missing"
        output = (root / value).resolve()
        if not inside(root, output) or not output.is_file() or sha256(output) not in qa_hashes:
            return f"promoted {key} output does not match render QA"
    return None


def project_requires_design_handoff(root: Path) -> bool:
    project_path = root / "project.yaml"
    if project_path.is_file():
        project = load_yaml(project_path)
        if int(project.get("workflow_contract_version", 0) or 0) >= 5:
            return True
    local_workflow = root / "config" / "workflow.yaml"
    if local_workflow.is_file():
        workflow = load_yaml(local_workflow)
        visualization = workflow.get("visualization_design") if isinstance(workflow.get("visualization_design"), dict) else {}
        return visualization.get("strict_handoff") is True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = args.manifest.resolve()
    payload = load_yaml(manifest_path)
    contracts = payload.get("figures", [])
    errors: list[dict[str, str]] = []
    copied: list[dict[str, str]] = []
    paper_figures = (root / "paper" / "figures").resolve()
    strict_design_handoff = project_requires_design_handoff(root)
    paper_figures.mkdir(parents=True, exist_ok=True)
    if not isinstance(contracts, list):
        errors.append({"code": "MANIFEST_SHAPE", "message": "figures must be a list"})
        contracts = []
    for contract in contracts:
        if not isinstance(contract, dict):
            errors.append({"code": "CONTRACT_SHAPE", "message": "contract must be an object"})
            continue
        identifier = str(contract.get("id", "unknown"))
        if contract.get("contract_version") != "2.0":
            errors.append({"code": "CONTRACT_VERSION", "message": f"{identifier} must use Figure Contract v2"})
            continue
        missing_enhanced = [field for field in ENHANCED_FIELDS if field not in contract]
        if missing_enhanced:
            errors.append({"code": "FIGURE_BRIEF_FIELDS", "message": f"{identifier} lacks enhanced Figure Contract fields: {', '.join(missing_enhanced)}"})
            continue
        if contract.get("palette_id") != "journal-spectrum-v2":
            errors.append({"code": "PALETTE_ID", "message": f"{identifier} must use journal-spectrum-v2"})
            continue
        if contract.get("min_font_pt", 0) < 8:
            errors.append({"code": "MIN_FONT", "message": f"{identifier} must use at least 8 pt at final size"})
            continue
        label_strategy = contract.get("label_strategy", {})
        if not isinstance(label_strategy, dict) or label_strategy.get("collision_checked") is not True:
            errors.append({"code": "LABEL_COLLISION_CHECK", "message": f"{identifier} must record a passed label collision check"})
            continue
        integrity = contract.get("data_integrity", {})
        if not isinstance(integrity, dict) or integrity.get("manual_values_forbidden") is not True:
            errors.append({"code": "DATA_INTEGRITY", "message": f"{identifier} must forbid manual result values"})
            continue
        if len(contract.get("panel_map", [])) > 1 and not str(contract.get("multipanel_justification", "")).strip():
            errors.append({"code": "MULTIPANEL_JUSTIFICATION", "message": f"{identifier} requires an explicit multi-panel justification"})
            continue
        output_values = contract.get("outputs", {})
        if not isinstance(output_values, dict):
            errors.append({"code": "CONTRACT_OUTPUTS", "message": f"{identifier} outputs must be an object"})
            continue
        output_paths = [(root / str(output_values.get(key, ""))).resolve() for key in ("pdf", "svg", "png")]
        if any(not inside(root, path) for path in output_paths):
            errors.append({"code": "PATH_ESCAPE", "message": f"{identifier} uses an output path outside the workspace"})
            continue
        extensions = {path.suffix.lower() for path in output_paths if path.is_file()}
        if not {".pdf", ".svg", ".png"}.issubset(extensions):
            errors.append({"code": "EXPORT_SET", "message": f"{identifier} lacks existing PDF/SVG/PNG outputs"})
            continue
        if output_values.get("png_dpi") != 400:
            errors.append({"code": "PNG_DPI", "message": f"{identifier} must declare png_dpi=400"})
            continue
        script = (root / str(contract.get("source_script", ""))).resolve()
        if not inside(root, script) or not script.is_file():
            errors.append({"code": "SOURCE_SCRIPT", "message": f"{identifier} source script does not exist"})
            continue
        if not isinstance(contract.get("evidence_chain"), list) or not contract["evidence_chain"]:
            errors.append({"code": "EVIDENCE_CHAIN", "message": f"{identifier} requires evidence_chain"})
            continue
        evidence_ok = True
        for evidence in contract["evidence_chain"]:
            if not isinstance(evidence, dict):
                evidence_ok = False
                continue
            locator = str(evidence.get("locator", ""))
            evidence_path = (root / locator.split(":", 1)[0]).resolve()
            if not inside(root, evidence_path) or not evidence_path.is_file() or evidence.get("sha256") != hashlib.sha256(evidence_path.read_bytes()).hexdigest():
                evidence_ok = False
        if not evidence_ok:
            errors.append({"code": "EVIDENCE_HASH", "message": f"{identifier} evidence hash is missing or stale"})
            continue
        if strict_design_handoff and contract.get("design_handoff") is None:
            errors.append({"code": "DESIGN_HANDOFF", "message": f"{identifier}: V5 project requires design_handoff"})
            continue
        handoff_error = validate_design_handoff(root, contract)
        if handoff_error:
            errors.append({"code": "DESIGN_HANDOFF", "message": f"{identifier}: {handoff_error}"})
            continue
        if not inside(paper_figures, output_paths[0]):
            errors.append({"code": "PAPER_OUTPUT", "message": f"{identifier} PDF output must be under paper/figures"})
            continue
        copied.append({"id": identifier, "outputs": {key: str(value) for key, value in output_values.items() if key in {"pdf", "svg", "png"}}})
    report = {"schema_version": 1, "passed": not errors, "copied": copied, "errors": errors}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
