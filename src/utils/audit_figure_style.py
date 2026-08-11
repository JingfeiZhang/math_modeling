"""Audit the shared figure palette and optional Figure Contract metadata."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.utils.figure_style import ROOT, STYLE_PATH, load_style, validate_grayscale  # noqa: E402


HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")
SOURCE_EXTENSIONS = {".py", ".m", ".tex", ".yaml", ".yml"}
SHARED_SCAN_DIRS = (ROOT / "src", ROOT / "matlab", ROOT / "templates")
ENHANCED_CONTRACT_FIELDS = (
    "core_message",
    "visual_hierarchy",
    "target_size_profile",
    "statistics_report",
    "data_integrity",
    "label_strategy",
    "rasterized_layers",
)


def scan_source_colors(allowed: set[str], project_root: Path | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    project = project_root.resolve() if project_root else ROOT
    directories = [*SHARED_SCAN_DIRS, project / "src", project / "matlab", project / "paper"]
    seen: set[Path] = set()
    for directory in directories:
        directory = directory.resolve()
        if directory in seen:
            continue
        seen.add(directory)
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            if any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            try:
                project_parts = path.relative_to(project).parts
            except ValueError:
                project_parts = ()
            if "staging" in project_parts or "_archive" in project_parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in HEX_RE.finditer(text):
                value = match.group(0).upper()
                if value not in allowed:
                    try:
                        label = path.relative_to(project).as_posix()
                    except ValueError:
                        label = "shared://" + path.relative_to(ROOT).as_posix()
                    findings.append({"file": label, "color": value})
    return findings


def audit_contracts(manifest: Path | None, strict: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if manifest is None or not manifest.is_file():
        return warnings, errors
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    figures = payload.get("figures", []) if isinstance(payload, dict) else []
    for figure in figures:
        identifier = figure.get("id", "unknown")
        missing = [field for field in ("palette_id", "color_encoding") if not figure.get(field)]
        if figure.get("palette_id") and figure["palette_id"] != "journal-spectrum-v2":
            errors.append({"code": "PALETTE_ID", "figure": identifier, "value": figure["palette_id"]})
        if missing:
            item = {"code": "PALETTE_METADATA", "figure": identifier, "missing": missing}
            (errors if strict else warnings).append(item)
        enhanced_missing = [field for field in ENHANCED_CONTRACT_FIELDS if field not in figure]
        if enhanced_missing:
            item = {"code": "FIGURE_BRIEF_METADATA", "figure": identifier, "missing": enhanced_missing}
            (errors if strict else warnings).append(item)
        label_strategy = figure.get("label_strategy")
        if isinstance(label_strategy, dict) and label_strategy.get("collision_checked") is not True:
            errors.append({"code": "LABEL_COLLISION_CHECK", "figure": identifier})
        integrity = figure.get("data_integrity")
        if isinstance(integrity, dict) and integrity.get("manual_values_forbidden") is not True:
            errors.append({"code": "MANUAL_VALUES_POLICY", "figure": identifier})
        panel_map = figure.get("panel_map", [])
        if isinstance(panel_map, list) and len(panel_map) > 1 and not str(figure.get("multipanel_justification", "")).strip():
            errors.append({"code": "MULTIPANEL_JUSTIFICATION", "figure": identifier})
    return warnings, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "figure_style_audit.json")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    config = load_style()
    palette_values = {value.upper() for value in config["colors"].values()}
    palette_values.update(value.upper() for value in config["categorical_order"])
    palette_values.update(value.upper() for value in config["rules"].get("allowed_derived_colors", []))
    unexpected = scan_source_colors(palette_values, args.project_root)
    warnings, errors = audit_contracts(args.manifest, args.strict)
    grayscale = validate_grayscale()
    if not grayscale["passed"]:
        errors.append({"code": "GRAYSCALE_CONTRAST", "checks": grayscale["checks"]})
    if unexpected:
        errors.append({"code": "UNREGISTERED_COLOR", "findings": unexpected})
    report = {
        "schema_version": 1,
        "palette_id": config["palette_id"],
        "config": str(STYLE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "grayscale": grayscale,
        "unexpected_colors": unexpected,
        "warnings": warnings,
        "errors": errors,
        "passed": not errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
