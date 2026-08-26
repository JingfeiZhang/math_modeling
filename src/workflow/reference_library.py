"""Read-only competition textbook quick-reference library.

The library is deliberately weaker than the academic-literature and Formal
evidence chains.  It helps P1-P3 choose model directions and risk probes; it
never writes project state, claims, paper sources, or release files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


CARD_FIELDS = {
    "card_id", "tags", "source_id", "source_sha256", "pdf_page", "printed_page",
    "chapter", "section", "locator_confidence", "visual_verification",
    "formula_manual_check_required",
}
MODULE_FIELDS = {
    "module_id", "module_version", "family", "tags", "source_cards",
    "stage_scope", "evidence_status", "contest_evidence_eligible",
    "allowed_use", "forbidden_use",
}
PLAYBOOK_FIELDS = {
    "playbook_id", "playbook_version", "tags", "modules", "stage_scope",
    "evidence_status", "contest_evidence_eligible", "allowed_use",
    "forbidden_use",
}
ALGORITHM_SOURCE_FIELDS = {
    "source_id", "repository", "commit", "commit_url", "language",
    "license_status", "scope", "source_paths", "last_checked",
}
ALGORITHM_CARD_FIELDS = {
    "algorithm_card_id", "source_id", "source_commit", "source_path",
    "tags", "stage_scope", "evidence_status", "contest_evidence_eligible",
    "allowed_use", "forbidden_use", "language", "license_status",
    "interface", "baseline_required", "baseline_options", "known_risks", "adaptation_required",
    "entry_points", "skeleton_path",
}
REQUIRED_CARD_SECTIONS = (
    "适用信号", "必要前提", "最小建模骨架", "算法/代码入口", "同输出 baseline",
    "验证与敏感性", "停止条件", "误用风险", "原书回退定位",
)
REQUIRED_MODULE_SECTION_PATTERNS = (
    r"(?:用途|适用)与排除",
    r"题面.*(?:映射|数学对象|变量和约束)",
    r"最小可运行",
    r"(?:baseline 到主模型)?升级路径",
    r"(?:三项)?关键诊断",
    r"失败回退",
    r"(?:赛中)?最小实验序列",
    r"(?:必须)?记录(?:的)?字段",
    r"论文交接边界",
    r"原书回退定位",
)
REQUIRED_PLAYBOOK_SECTIONS = (
    "触发与排除", "输入输出合同", "分阶段行动", "baseline 与升级",
    "联合诊断", "停止与回退", "Candidate 交接", "禁止事项",
)
SAFE_SOURCE_ID = re.compile(r"^[a-z0-9-]+$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
CORE_TAGS = ("optimization", "metaheuristic", "uncertainty", "statistics", "numerical", "machine-learning", "dynamics", "mechanism")
EARLY_STAGES = ("P1", "P2", "P3a", "P3b")
ALLOWED_USES = {"model_direction", "assumption_check", "baseline_design", "risk_probe"}
FORBIDDEN_USES = {"academic_citation", "formal_evidence", "claim_support", "figure_contract", "submission"}
LAYERS = ("card", "module", "playbook", "code", "all")
ALGORITHM_ENTRY_KINDS = {"function", "class", "script"}
MIRROR_IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache"}
MIRROR_TEXT_SUFFIXES = {
    ".py", ".pyi", ".m", ".mlx", ".ipynb", ".md", ".txt", ".yaml", ".yml", ".json",
    ".toml", ".ini", ".cfg", ".csv", ".tsv", ".tex", ".r", ".R", ".jl", ".cpp", ".h",
}
MIRROR_MAX_TEXT_BYTES = 2 * 1024 * 1024
MIRROR_QUERY_LIMIT = 20
# Require a path boundary before a Windows drive prefix so URLs such as
# ``https://...`` are not mistaken for ``s:/...``.
ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/Users/|/home/|C:/Users/)")


def _relative_ref(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and not re.match(r"^[A-Za-z]:", value) and ".." not in path.parts


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def library_root(workspace_root: Path) -> Path:
    """Return the repository root used by the library, never the PDF root."""

    return workspace_root.resolve()


def load_sources(workspace_root: Path) -> dict[str, Any]:
    path = library_root(workspace_root) / "references" / "competition-knowledge" / "sources.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"source manifest is missing: {path}")
    payload = _read_yaml(path)
    issues = validate_sources(payload)
    schema_path = path.with_name("sources.schema.json")
    if not schema_path.is_file():
        issues.append(f"source manifest schema is missing: {schema_path}")
    else:
        from jsonschema import Draft202012Validator

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        issues.extend(error.message for error in Draft202012Validator(schema).iter_errors(payload))
    if issues:
        raise ValueError("invalid reference source manifest: " + "; ".join(issues))
    return payload


def validate_sources(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != 1:
        issues.append("schema_version must be 1")
    policy = payload.get("evidence_policy")
    if not isinstance(policy, dict) or policy.get("contest_evidence_eligible") is not False:
        issues.append("reference library must never be contest evidence")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        return [*issues, "sources must be a non-empty list"]
    seen: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            issues.append(f"sources[{index}] must be an object")
            continue
        required = {"source_id", "filename", "sha256", "pages", "locator_rule", "extractability", "locator_status"}
        missing = sorted(required - set(source))
        if missing:
            issues.append(f"sources[{index}] missing {missing}")
        source_id = str(source.get("source_id", ""))
        if not SAFE_SOURCE_ID.fullmatch(source_id):
            issues.append(f"sources[{index}] has invalid source_id")
        if source_id in seen:
            issues.append(f"duplicate source_id: {source_id}")
        seen.add(source_id)
        filename = str(source.get("filename", ""))
        if not filename or Path(filename).is_absolute() or ":" in filename or "\\" in filename or "/" in filename:
            issues.append(f"sources[{index}] filename must be a basename")
        if not SHA256.fullmatch(str(source.get("sha256", ""))):
            issues.append(f"sources[{index}] sha256 must be 64 hex characters")
        if not isinstance(source.get("pages"), int) or source.get("pages", 0) < 1:
            issues.append(f"sources[{index}] pages must be a positive integer")
    return issues


def _frontmatter(item_path: Path) -> tuple[dict[str, Any], str]:
    text = item_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"knowledge item has no YAML front matter: {item_path}")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"knowledge item front matter is not closed: {item_path}")
    data = yaml.safe_load(parts[1])
    return (data if isinstance(data, dict) else {}), parts[2]


def validate_card(card_path: Path, sources_by_id: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    try:
        front, body = _frontmatter(card_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    missing = sorted(CARD_FIELDS - set(front))
    if missing:
        issues.append(f"{card_path.name} missing {missing}")
    card_id = str(front.get("card_id", ""))
    if not SAFE_SOURCE_ID.fullmatch(card_id):
        issues.append(f"{card_path.name} has invalid card_id")
    tags = front.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) for tag in tags):
        issues.append(f"{card_path.name} tags must be a non-empty string list")
    source_id = str(front.get("source_id", ""))
    source = sources_by_id.get(source_id)
    if source is None:
        issues.append(f"{card_path.name} references unknown source_id: {source_id}")
    elif str(front.get("source_sha256", "")).lower() != str(source["sha256"]).lower():
        issues.append(f"{card_path.name} source_sha256 does not match sources.yaml")
    if front.get("formula_manual_check_required") is not True:
        issues.append(f"{card_path.name} must require manual formula checking")
    if str(front.get("visual_verification", "")) not in {"pending", "verified"}:
        issues.append(f"{card_path.name} visual_verification must be pending or verified")
    if not body.strip():
        issues.append(f"{card_path.name} body is empty")
    for section in REQUIRED_CARD_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", body, re.MULTILINE):
            issues.append(f"{card_path.name} missing section: {section}")
    if ABSOLUTE_PATH.search(card_path.read_text(encoding="utf-8")):
        issues.append(f"{card_path.name} contains an absolute path")
    return issues


def card_records(workspace_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    sources = load_sources(workspace_root)
    by_id = {item["source_id"]: item for item in sources["sources"]}
    card_dir = library_root(workspace_root) / "references" / "competition-knowledge" / "cards"
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    seen_ids: set[str] = set()
    for path in sorted(card_dir.glob("*.md")) if card_dir.is_dir() else []:
        card_issues = validate_card(path, by_id)
        try:
            front, body = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError):
            issues.extend(card_issues)
            continue
        card_id = str(front.get("card_id", path.stem))
        if card_id in seen_ids:
            card_issues.append(f"duplicate card_id: {card_id}")
        seen_ids.add(card_id)
        issues.extend(card_issues)
        records.append({
            "path": path,
            "card_id": card_id,
            "tags": [str(item).lower() for item in front.get("tags", []) if isinstance(item, str)],
            "source_id": front.get("source_id", ""),
            "source_sha256": str(front.get("source_sha256", "")).lower(),
            "pdf_page": front.get("pdf_page"),
            "printed_page": front.get("printed_page"),
            "chapter": front.get("chapter", ""),
            "section": front.get("section", ""),
            "locator_confidence": front.get("locator_confidence", "low"),
            "body": body,
            "valid": not card_issues,
        })
    return records, issues


def _validate_non_evidence_contract(item_path: Path, front: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    stage_scope = front.get("stage_scope")
    if (
        not isinstance(stage_scope, list)
        or not stage_scope
        or any(stage not in EARLY_STAGES for stage in stage_scope)
    ):
        issues.append(f"{item_path.name} stage_scope must stay within P1-P3")
    if front.get("evidence_status") != "P1-P3-non-evidence":
        issues.append(f"{item_path.name} evidence_status must be P1-P3-non-evidence")
    if front.get("contest_evidence_eligible") is not False:
        issues.append(f"{item_path.name} must never be contest evidence")
    allowed_use = front.get("allowed_use")
    if not isinstance(allowed_use, list) or set(allowed_use) != ALLOWED_USES:
        issues.append(f"{item_path.name} allowed_use must use the fixed exploration roles")
    forbidden_use = front.get("forbidden_use")
    if not isinstance(forbidden_use, list) or not FORBIDDEN_USES <= set(forbidden_use):
        issues.append(f"{item_path.name} forbidden_use is incomplete")
    if ABSOLUTE_PATH.search(item_path.read_text(encoding="utf-8")):
        issues.append(f"{item_path.name} contains an absolute path")
    return issues


def validate_module(module_path: Path, cards_by_id: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    try:
        front, body = _frontmatter(module_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    missing = sorted(MODULE_FIELDS - set(front))
    if missing:
        issues.append(f"{module_path.name} missing {missing}")
    module_id = str(front.get("module_id", ""))
    if not SAFE_SOURCE_ID.fullmatch(module_id):
        issues.append(f"{module_path.name} has invalid module_id")
    if front.get("module_version") != 1:
        issues.append(f"{module_path.name} module_version must be 1")
    if not isinstance(front.get("family"), str) or not front.get("family"):
        issues.append(f"{module_path.name} family must be a non-empty string")
    tags = front.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) for tag in tags):
        issues.append(f"{module_path.name} tags must be a non-empty string list")
    source_cards = front.get("source_cards")
    if not isinstance(source_cards, list) or not source_cards:
        issues.append(f"{module_path.name} source_cards must be non-empty")
    else:
        for card_id in source_cards:
            card = cards_by_id.get(str(card_id))
            if card is None:
                issues.append(f"{module_path.name} references unknown source card: {card_id}")
            elif not card["valid"]:
                issues.append(f"{module_path.name} references invalid source card: {card_id}")
    issues.extend(_validate_non_evidence_contract(module_path, front))
    for pattern in REQUIRED_MODULE_SECTION_PATTERNS:
        if not re.search(rf"^##\s+(?:\d+\.\s*)?{pattern}.*$", body, re.MULTILINE | re.IGNORECASE):
            issues.append(f"{module_path.name} missing module section matching: {pattern}")
    return issues


def module_records(workspace_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    cards, card_issues = card_records(workspace_root)
    cards_by_id = {str(item["card_id"]): item for item in cards}
    module_dir = library_root(workspace_root) / "references" / "competition-knowledge" / "modules"
    records: list[dict[str, Any]] = []
    issues = list(card_issues)
    seen_ids: set[str] = set()
    for path in sorted(module_dir.rglob("*.md")) if module_dir.is_dir() else []:
        module_issues = validate_module(path, cards_by_id)
        try:
            front, body = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError):
            issues.extend(module_issues)
            continue
        module_id = str(front.get("module_id", path.stem))
        if module_id in seen_ids:
            module_issues.append(f"duplicate module_id: {module_id}")
        seen_ids.add(module_id)
        issues.extend(module_issues)
        records.append({
            "path": path,
            "module_id": module_id,
            "family": front.get("family", ""),
            "tags": sorted({
                *[str(item).lower() for item in front.get("tags", []) if isinstance(item, str)],
                str(front.get("family", "")).lower(),
            } - {""}),
            "source_cards": [str(item) for item in front.get("source_cards", [])],
            "stage_scope": list(front.get("stage_scope", [])),
            "body": body,
            "valid": not module_issues,
        })
    return records, issues


def validate_playbook(playbook_path: Path, modules_by_id: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    try:
        front, body = _frontmatter(playbook_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    missing = sorted(PLAYBOOK_FIELDS - set(front))
    if missing:
        issues.append(f"{playbook_path.name} missing {missing}")
    playbook_id = str(front.get("playbook_id", ""))
    if not SAFE_SOURCE_ID.fullmatch(playbook_id):
        issues.append(f"{playbook_path.name} has invalid playbook_id")
    if front.get("playbook_version") != 1:
        issues.append(f"{playbook_path.name} playbook_version must be 1")
    tags = front.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) for tag in tags):
        issues.append(f"{playbook_path.name} tags must be a non-empty string list")
    modules = front.get("modules")
    if not isinstance(modules, list) or not modules:
        issues.append(f"{playbook_path.name} modules must be non-empty")
    else:
        for module_id in modules:
            module = modules_by_id.get(str(module_id))
            if module is None:
                issues.append(f"{playbook_path.name} references unknown module: {module_id}")
            elif not module["valid"]:
                issues.append(f"{playbook_path.name} references invalid module: {module_id}")
    issues.extend(_validate_non_evidence_contract(playbook_path, front))
    for section in REQUIRED_PLAYBOOK_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", body, re.MULTILINE):
            issues.append(f"{playbook_path.name} missing section: {section}")
    return issues


def playbook_records(workspace_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    modules, module_issues = module_records(workspace_root)
    modules_by_id = {str(item["module_id"]): item for item in modules}
    playbook_dir = library_root(workspace_root) / "references" / "competition-knowledge" / "playbooks"
    records: list[dict[str, Any]] = []
    issues = list(module_issues)
    seen_ids: set[str] = set()
    playbook_paths = [path for path in sorted(playbook_dir.glob("*.md")) if path.name != "index.md"] if playbook_dir.is_dir() else []
    for path in playbook_paths:
        playbook_issues = validate_playbook(path, modules_by_id)
        try:
            front, body = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError):
            issues.extend(playbook_issues)
            continue
        playbook_id = str(front.get("playbook_id", path.stem))
        if playbook_id in seen_ids:
            playbook_issues.append(f"duplicate playbook_id: {playbook_id}")
        seen_ids.add(playbook_id)
        issues.extend(playbook_issues)
        records.append({
            "path": path,
            "playbook_id": playbook_id,
            "tags": [str(item).lower() for item in front.get("tags", []) if isinstance(item, str)],
            "modules": [str(item) for item in front.get("modules", [])],
            "stage_scope": list(front.get("stage_scope", [])),
            "body": body,
            "valid": not playbook_issues,
        })
    return records, issues


def _algorithm_root(workspace_root: Path) -> Path:
    return library_root(workspace_root) / "references" / "algorithm-sources"


def _algorithm_mirror_path(workspace_root: Path, source: dict[str, Any]) -> Path:
    relative = str(source.get("mirror_relpath") or "")
    if not relative:
        relative = f"tools/algorithm-sources/{source['source_id']}/{source['commit']}"
    if not _relative_ref(relative):
        raise ValueError(f"algorithm mirror path is unsafe: {relative}")
    root = library_root(workspace_root)
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError(f"algorithm mirror path escapes workspace: {relative}")
    return target


def _mirror_state_path(mirror_path: Path) -> Path:
    return mirror_path / "mirror_state.json"


def _algorithm_index_root(workspace_root: Path, source: dict[str, Any]) -> Path:
    relative = str(source.get("index_relpath") or f"tools/algorithm-sources/{source['source_id']}/{source['commit']}")
    if not _relative_ref(relative):
        raise ValueError(f"algorithm index path is unsafe: {relative}")
    root = library_root(workspace_root)
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError(f"algorithm index path escapes workspace: {relative}")
    return target


def _run_git(arguments: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = ["git", *arguments]
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git_head(mirror_path: Path) -> str | None:
    if not (mirror_path / ".git").exists():
        return None
    result = _run_git(["rev-parse", "HEAD"], cwd=mirror_path)
    if result.returncode != 0:
        return None
    return result.stdout.strip().lower()


def _mirror_relpath(workspace_root: Path, mirror_path: Path) -> str:
    return mirror_path.resolve().relative_to(library_root(workspace_root)).as_posix()


def _license_files(mirror_path: Path) -> list[str]:
    candidates: list[str] = []
    for path in mirror_path.iterdir() if mirror_path.is_dir() else []:
        if path.is_file() and re.fullmatch(r"(?i)(license|copying)(?:\.[A-Za-z0-9._-]+)?", path.name):
            candidates.append(path.name)
    return sorted(candidates)


def _extract_symbols(text: str, suffix: str) -> list[dict[str, Any]]:
    patterns: list[tuple[str, str]] = []
    if suffix in {".py", ".pyi"}:
        patterns = [("function", r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("), ("class", r"^\s*class\s+([A-Za-z_]\w*)\s*[:(]")]
    elif suffix in {".m", ".mlx"}:
        patterns = [("function", r"^\s*function(?:\s+\[[^\]]*\]|\s+[^=]+\s*=)?\s*([A-Za-z_]\w*)\s*\(")]
    symbols: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in patterns:
            match = re.search(pattern, line)
            if match:
                symbols.append({"symbol": match.group(1), "kind": kind, "line": line_number})
    return symbols


def _build_mirror_index(workspace_root: Path, source: dict[str, Any], mirror_path: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    root = mirror_path.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in MIRROR_IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        relative = path.relative_to(root).as_posix()
        digest = _sha256_file(path)
        suffix = path.suffix
        text_readable = suffix in MIRROR_TEXT_SUFFIXES and path.stat().st_size <= MIRROR_MAX_TEXT_BYTES
        symbols: list[dict[str, Any]] = []
        if text_readable:
            try:
                symbols = _extract_symbols(path.read_text(encoding="utf-8"), suffix)
            except (OSError, UnicodeDecodeError):
                text_readable = False
        files.append({
            "path": relative,
            "suffix": suffix,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "text_readable": text_readable,
            "symbols": symbols,
        })
    synced_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 1,
        "source_id": source["source_id"],
        "commit": source["commit"],
        "mirror_mode": source.get("mirror_mode", "git_clone"),
        "mirror_path": _mirror_relpath(workspace_root, mirror_path),
        "head_verified": _git_head(mirror_path) == str(source["commit"]).lower(),
        "generated_at_utc": synced_at,
        "synced_at": synced_at,
        "file_count": len(files),
        "files": files,
    }
    index_root = _algorithm_index_root(workspace_root, source)
    index_root.mkdir(parents=True, exist_ok=True)
    index_path = index_root / "algorithm_index.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _mirror_status(workspace_root: Path, source: dict[str, Any]) -> dict[str, Any]:
    mirror_path = _algorithm_mirror_path(workspace_root, source)
    relative = _mirror_relpath(workspace_root, mirror_path)
    if not mirror_path.exists():
        return {"status": "NOT_SYNCED", "mirror_path": relative, "head": None, "index_path": None}
    mirror_mode = str(source.get("mirror_mode", "git_clone"))
    head = _git_head(mirror_path)
    if mirror_mode == "git_clone":
        if not (mirror_path / ".git").exists():
            return {"status": "INVALID", "mirror_path": relative, "head": None, "index_path": None}
        if head != str(source["commit"]).lower():
            return {"status": "STALE", "mirror_path": relative, "head": head, "index_path": None}
    elif mirror_mode != "local_directory":
        return {"status": "INVALID", "mirror_path": relative, "head": head, "index_path": None}
    index_root = _algorithm_index_root(workspace_root, source)
    index = _load_mirror_index(index_root)
    if index is None:
        return {"status": "STALE", "mirror_path": relative, "head": head, "index_path": relative + "/algorithm_index.json"}
    if str(index.get("source_id")) != str(source.get("source_id")) or str(index.get("commit")).lower() != str(source.get("commit")).lower():
        return {"status": "STALE", "mirror_path": relative, "head": head, "index_path": str(source.get("index_relpath") or relative) + "/algorithm_index.json"}
    expected_files = {
        str(row.get("path")): str(row.get("sha256", "")).lower()
        for row in index.get("files", [])
        if isinstance(row, dict) and row.get("path")
    }
    current_files: dict[str, str] = {}
    for path in sorted(mirror_path.rglob("*")):
        if not path.is_file() or any(part in MIRROR_IGNORED_DIRS for part in path.relative_to(mirror_path).parts):
            continue
        if path.name in {"mirror_state.json", "algorithm_index.json"}:
            continue
        current_files[path.relative_to(mirror_path).as_posix()] = _sha256_file(path)
    if current_files != expected_files:
        return {"status": "STALE", "mirror_path": relative, "head": head, "index_path": str(source.get("index_relpath") or relative) + "/algorithm_index.json"}
    return {"status": "READY", "mirror_path": relative, "head": head, "index_path": str(source.get("index_relpath") or relative) + "/algorithm_index.json"}


def sync_algorithm_source(workspace_root: Path, source_id: str) -> dict[str, Any]:
    """Clone and index one pinned source; never execute files from the source."""

    sources = load_algorithm_sources(workspace_root)
    source = next((item for item in sources["sources"] if item.get("source_id") == source_id), None)
    if source is None:
        raise ValueError(f"unknown algorithm source_id: {source_id}")
    target = _algorithm_mirror_path(workspace_root, source)
    if str(source.get("mirror_mode", "git_clone")) == "local_directory":
        if not target.is_dir():
            return {"schema_version": 1, "passed": False, "status": "NOT_FOUND", "mirror_path": _mirror_relpath(workspace_root, target)}
        index = _build_mirror_index(workspace_root, source, target)
        index["license_status"] = str(source.get("license_status", "UNKNOWN"))
        index["license_files"] = _license_files(target)
        index_root = _algorithm_index_root(workspace_root, source)
        index_root.mkdir(parents=True, exist_ok=True)
        state_path = index_root / "mirror_state.json"
        state_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state = _mirror_status(workspace_root, source)
        return {"schema_version": 1, "passed": state["status"] == "READY", "status": state["status"], **state}
    if shutil.which("git") is None:
        raise RuntimeError("git is required to sync algorithm sources")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    existing_status = _mirror_status(workspace_root, source)
    if existing_status["status"] == "STALE":
        return {"schema_version": 1, "passed": False, "status": "MIRROR_COMMIT_MISMATCH", **existing_status}
    if existing_status["status"] == "INVALID":
        return {"schema_version": 1, "passed": False, "status": "MIRROR_INVALID", **existing_status}
    if existing_status["status"] == "NOT_SYNCED":
        temporary = Path(tempfile.mkdtemp(prefix=f".{source_id}-", dir=parent))
        try:
            env = os.environ.copy()
            env["GIT_LFS_SKIP_SMUDGE"] = "1"
            clone = _run_git(["clone", "--no-tags", "--depth", "1", "--no-checkout", str(source["repository"]), str(temporary)], env=env)
            if clone.returncode != 0:
                raise RuntimeError(f"git clone failed: {clone.stderr.strip() or clone.stdout.strip()}")
            checkout = _run_git(["checkout", "--detach", "--force", str(source["commit"])], cwd=temporary, env=env)
            if checkout.returncode != 0:
                raise RuntimeError(f"git checkout failed: {checkout.stderr.strip() or checkout.stdout.strip()}")
            if _git_head(temporary) != str(source["commit"]).lower():
                raise RuntimeError("cloned source HEAD does not match the pinned commit")
            temporary_state = _build_mirror_index(workspace_root, source, temporary)
            temporary_state["license_status"] = str(source.get("license_status", "UNKNOWN"))
            temporary_state["license_files"] = _license_files(temporary)
            _mirror_state_path(temporary).write_text(json.dumps(temporary_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            shutil.move(str(temporary), str(target))
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    else:
        index = _build_mirror_index(workspace_root, source, target)
        index["license_status"] = str(source.get("license_status", "UNKNOWN"))
        index["license_files"] = _license_files(target)
        _mirror_state_path(target).write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = _mirror_status(workspace_root, source)
    final_status = "READY" if state["status"] == "READY" else "INVALID"
    return {"schema_version": 1, "passed": final_status == "READY", "status": final_status, **state}


def load_algorithm_sources(workspace_root: Path) -> dict[str, Any]:
    """Load pinned GitHub metadata; syncing is always an explicit action."""

    root = _algorithm_root(workspace_root)
    path = root / "sources.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"algorithm source manifest is missing: {path}")
    payload = _read_yaml(path)
    issues = validate_algorithm_sources(payload)
    schema_path = root / "sources.schema.json"
    if not schema_path.is_file():
        issues.append(f"algorithm source schema is missing: {schema_path}")
    else:
        from jsonschema import Draft202012Validator

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        issues.extend(error.message for error in Draft202012Validator(schema).iter_errors(payload))
    if issues:
        raise ValueError("invalid algorithm source manifest: " + "; ".join(issues))
    return payload


def validate_algorithm_sources(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != 1:
        issues.append("algorithm source schema_version must be 1")
    policy = payload.get("evidence_policy")
    if not isinstance(policy, dict) or policy.get("contest_evidence_eligible") is not False:
        issues.append("algorithm sources must never be contest evidence")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        return [*issues, "algorithm sources must be a non-empty list"]
    seen: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            issues.append(f"algorithm sources[{index}] must be an object")
            continue
        missing = sorted(ALGORITHM_SOURCE_FIELDS - set(source))
        if missing:
            issues.append(f"algorithm sources[{index}] missing {missing}")
        source_id = str(source.get("source_id", ""))
        if not SAFE_SOURCE_ID.fullmatch(source_id):
            issues.append(f"algorithm sources[{index}] has invalid source_id")
        if source_id in seen:
            issues.append(f"duplicate algorithm source_id: {source_id}")
        seen.add(source_id)
        repository = str(source.get("repository", ""))
        if not re.fullmatch(r"https://github\.com/[^/]+/[^/]+/?", repository):
            issues.append(f"algorithm sources[{index}] repository must be a GitHub HTTPS URL")
        commit = str(source.get("commit", ""))
        if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
            issues.append(f"algorithm sources[{index}] commit must be a 40-character SHA")
        paths = source.get("source_paths")
        if not isinstance(paths, list) or not paths:
            issues.append(f"algorithm sources[{index}] source_paths must be non-empty")
        else:
            for value in paths:
                if not isinstance(value, str) or not _relative_ref(value):
                    issues.append(f"algorithm sources[{index}] contains an unsafe source path")
        mirror_relpath = source.get("mirror_relpath")
        if mirror_relpath is not None and (not isinstance(mirror_relpath, str) or not _relative_ref(mirror_relpath)):
            issues.append(f"algorithm sources[{index}] mirror_relpath must be a safe relative path")
        index_relpath = source.get("index_relpath")
        if index_relpath is not None and (not isinstance(index_relpath, str) or not _relative_ref(index_relpath)):
            issues.append(f"algorithm sources[{index}] index_relpath must be a safe relative path")
        mirror_mode = source.get("mirror_mode", "git_clone")
        if mirror_mode not in {"git_clone", "local_directory"}:
            issues.append(f"algorithm sources[{index}] mirror_mode is invalid")
    return issues


REQUIRED_ALGORITHM_CARD_SECTIONS = (
    "适用信号", "输入输出", "baseline 与升级", "验证要求",
    "已知风险", "停止与回退", "适配步骤", "来源与边界",
)


def validate_algorithm_card(card_path: Path, sources_by_id: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    try:
        front, body = _frontmatter(card_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    missing = sorted(ALGORITHM_CARD_FIELDS - set(front))
    if missing:
        issues.append(f"{card_path.name} missing {missing}")
    card_id = str(front.get("algorithm_card_id", ""))
    if not SAFE_SOURCE_ID.fullmatch(card_id):
        issues.append(f"{card_path.name} has invalid algorithm_card_id")
    source_id = str(front.get("source_id", ""))
    source = sources_by_id.get(source_id)
    if source is None:
        issues.append(f"{card_path.name} references unknown algorithm source_id: {source_id}")
    else:
        if str(front.get("source_commit", "")).lower() != str(source["commit"]).lower():
            issues.append(f"{card_path.name} source_commit does not match sources.yaml")
        if str(front.get("license_status", "")) != str(source["license_status"]):
            issues.append(f"{card_path.name} license_status does not match sources.yaml")
    tags = front.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) for tag in tags):
        issues.append(f"{card_path.name} tags must be a non-empty string list")
    stage_scope = front.get("stage_scope")
    if not isinstance(stage_scope, list) or not stage_scope or any(stage not in EARLY_STAGES for stage in stage_scope):
        issues.append(f"{card_path.name} stage_scope must stay within P1-P3")
    if front.get("evidence_status") != "P1-P3-non-evidence":
        issues.append(f"{card_path.name} evidence_status must be P1-P3-non-evidence")
    if front.get("contest_evidence_eligible") is not False:
        issues.append(f"{card_path.name} must never be contest evidence")
    if set(front.get("allowed_use", [])) != ALLOWED_USES:
        issues.append(f"{card_path.name} allowed_use must use the fixed exploration roles")
    if not {"formal_evidence", "claim_support", "figure_contract", "submission", "release", "direct_copy"} <= set(front.get("forbidden_use", [])):
        issues.append(f"{card_path.name} forbidden_use is incomplete")
    source_path = str(front.get("source_path", ""))
    if not source_path or not _relative_ref(source_path):
        issues.append(f"{card_path.name} source_path must be a safe relative path")
    entry_points = front.get("entry_points")
    if not isinstance(entry_points, list) or not entry_points:
        issues.append(f"{card_path.name} entry_points must be a non-empty list")
    else:
        for index, entry in enumerate(entry_points):
            if not isinstance(entry, dict):
                issues.append(f"{card_path.name} entry_points[{index}] must be an object")
                continue
            required_entry = {"path", "symbol", "kind", "purpose", "input", "output", "file_sha256"}
            missing_entry = sorted(required_entry - set(entry))
            if missing_entry:
                issues.append(f"{card_path.name} entry_points[{index}] missing {missing_entry}")
            if not _relative_ref(str(entry.get("path", ""))):
                issues.append(f"{card_path.name} entry_points[{index}] path must be relative")
            if str(entry.get("kind", "")) not in ALGORITHM_ENTRY_KINDS:
                issues.append(f"{card_path.name} entry_points[{index}] kind is invalid")
            if not SHA256.fullmatch(str(entry.get("file_sha256", ""))):
                issues.append(f"{card_path.name} entry_points[{index}] file_sha256 is invalid")
            locator = str(entry.get("locator_url", ""))
            pinned_commit = str(front.get("source_commit", ""))
            if locator and not any(
                marker in locator
                for marker in (f"/blob/{pinned_commit}/", f"/tree/{pinned_commit}/", f"/commit/{pinned_commit}")
            ):
                issues.append(f"{card_path.name} entry_points[{index}] locator_url must use the pinned commit")
    skeleton_path = str(front.get("skeleton_path", ""))
    if not skeleton_path or not _relative_ref(skeleton_path) or not skeleton_path.startswith("references/algorithm-sources/skeletons/"):
        issues.append(f"{card_path.name} skeleton_path must point to a safe local skeleton")
    baseline_options = front.get("baseline_options")
    if not isinstance(baseline_options, list) or not baseline_options:
        issues.append(f"{card_path.name} baseline_options must be a non-empty list")
    elif any(not isinstance(item, dict) or not {"id", "when", "required"} <= set(item) for item in baseline_options):
        issues.append(f"{card_path.name} baseline_options entries are incomplete")
    if not body.strip():
        issues.append(f"{card_path.name} body is empty")
    for section in REQUIRED_ALGORITHM_CARD_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", body, re.MULTILINE):
            issues.append(f"{card_path.name} missing section: {section}")
    if ABSOLUTE_PATH.search(card_path.read_text(encoding="utf-8")):
        issues.append(f"{card_path.name} contains an absolute path")
    return issues


def algorithm_records(workspace_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        sources = load_algorithm_sources(workspace_root)
    except FileNotFoundError as exc:
        return [], [str(exc)]
    sources_by_id = {str(item["source_id"]): item for item in sources["sources"]}
    card_dir = _algorithm_root(workspace_root) / "cards"
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    seen_ids: set[str] = set()
    for path in sorted(card_dir.glob("*.md")) if card_dir.is_dir() else []:
        card_issues = validate_algorithm_card(path, sources_by_id)
        try:
            front, body = _frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError):
            issues.extend(card_issues)
            continue
        card_id = str(front.get("algorithm_card_id", path.stem))
        if card_id in seen_ids:
            card_issues.append(f"duplicate algorithm_card_id: {card_id}")
        seen_ids.add(card_id)
        issues.extend(card_issues)
        records.append({
            "path": path,
            "algorithm_card_id": card_id,
            "source_id": str(front.get("source_id", "")),
            "source_commit": str(front.get("source_commit", "")).lower(),
            "source_path": str(front.get("source_path", "")),
            "tags": [str(item).lower() for item in front.get("tags", []) if isinstance(item, str)],
            "stage_scope": list(front.get("stage_scope", [])),
            "language": str(front.get("language", "")),
            "license_status": str(front.get("license_status", "")),
            "interface": str(front.get("interface", "")),
            "baseline_required": list(front.get("baseline_required", [])),
            "baseline_options": list(front.get("baseline_options", [])),
            "known_risks": list(front.get("known_risks", [])),
            "adaptation_required": list(front.get("adaptation_required", [])),
            "entry_points": list(front.get("entry_points", [])),
            "skeleton_path": str(front.get("skeleton_path", "")),
            "body": body,
            "valid": not card_issues,
        })
    return records, issues


def _local_mapping(workspace_root: Path) -> dict[str, Any]:
    mapping_path = library_root(workspace_root) / "work" / "reference-library" / "sources.local.yaml"
    if mapping_path.is_file():
        value = _read_yaml(mapping_path)
        return value if isinstance(value, dict) else {}
    return {}


def validate_local_mapping(mapping: dict[str, Any], sources_by_id: dict[str, dict[str, Any]]) -> list[str]:
    """Validate an ignored local PDF mapping without reading any PDF bytes."""

    if not mapping:
        return []
    issues: list[str] = []
    allowed = {"root", "library_root", "sources"}
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        issues.append(f"local mapping has unsupported fields: {unknown}")
    if mapping.get("root") and mapping.get("library_root"):
        issues.append("local mapping cannot define both root and library_root")
    for key in ("root", "library_root"):
        value = mapping.get(key)
        if value is not None and (not isinstance(value, str) or not Path(value).is_absolute()):
            issues.append(f"local mapping {key} must be an absolute path")
    source_map = mapping.get("sources")
    if source_map is not None and not isinstance(source_map, dict):
        issues.append("local mapping sources must be an object")
    if isinstance(source_map, dict):
        for source_id, value in source_map.items():
            if source_id not in sources_by_id:
                issues.append(f"local mapping references unknown source_id: {source_id}")
            if not isinstance(value, str) or not Path(value).is_absolute():
                issues.append(f"local mapping source {source_id} must be an absolute path")
    return issues


def _pdf_path(workspace_root: Path, source: dict[str, Any], mapping: dict[str, Any]) -> Path | None:
    env_root = os.environ.get("MATHMODEL_REFERENCE_LIBRARY_ROOT", "").strip()
    roots: list[Path] = []
    if env_root:
        roots.append(Path(env_root).expanduser())
    configured_root = mapping.get("root") or mapping.get("library_root")
    if configured_root:
        roots.append(Path(str(configured_root)).expanduser())
    source_map = mapping.get("sources") if isinstance(mapping.get("sources"), dict) else {}
    mapped = source_map.get(source["source_id"])
    if mapped:
        candidate = Path(str(mapped)).expanduser()
        return candidate if candidate.is_absolute() else (library_root(workspace_root) / candidate).resolve()
    for root in roots:
        candidate = root / str(source["filename"])
        if candidate.is_file():
            return candidate.resolve()
    return (roots[0] / str(source["filename"])).resolve() if roots else None


def verify(workspace_root: Path) -> dict[str, Any]:
    sources = load_sources(workspace_root)
    mapping = _local_mapping(workspace_root)
    sources_by_id = {item["source_id"]: item for item in sources["sources"]}
    mapping_issues = validate_local_mapping(mapping, sources_by_id)
    if mapping_issues:
        return {
            "schema_version": 1,
            "passed": False,
            "sources": [],
            "mapping_issues": mapping_issues,
            "warning": None,
        }
    rows: list[dict[str, Any]] = []
    for source in sources["sources"]:
        path = _pdf_path(workspace_root, source, mapping)
        row: dict[str, Any] = {"source_id": source["source_id"], "filename": source["filename"], "expected_sha256": source["sha256"].lower()}
        if path is None or not path.is_file():
            row.update({"status": "MISSING", "path_configured": path is not None})
        else:
            digest = _sha256_file(path)
            row.update({"status": "PASS" if digest.lower() == source["sha256"].lower() else "HASH_MISMATCH", "sha256": digest, "pages_expected": source["pages"]})
        rows.append(row)
    mapping_available = bool(mapping or os.environ.get("MATHMODEL_REFERENCE_LIBRARY_ROOT"))
    return {
        "schema_version": 1,
        "passed": not mapping_available or all(row["status"] == "PASS" for row in rows),
        "sources": rows,
        "mapping_issues": [],
        "warning": "No local PDF mapping configured; Markdown cards remain searchable." if not mapping_available else None,
    }


def _algorithm_source_map(workspace_root: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = load_algorithm_sources(workspace_root)
    except FileNotFoundError:
        return {}
    return {str(item["source_id"]): item for item in payload.get("sources", [])}


def _load_mirror_index(mirror_path: Path) -> dict[str, Any] | None:
    index_path = mirror_path / "algorithm_index.json"
    if not index_path.is_file():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and isinstance(payload.get("files"), list) else None


def _local_entry_points(workspace_root: Path, item: dict[str, Any], source: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    if source is None:
        return {"status": "INVALID", "mirror_path": None, "entry_points": [], "file_matches": []}, [f"unknown algorithm source: {item['source_id']}"]
    mirror = _mirror_status(workspace_root, source)
    result: dict[str, Any] = {
        "status": mirror["status"],
        "mirror_path": mirror["mirror_path"],
        "entry_points": [],
        "file_matches": [],
    }
    warnings: list[str] = []
    if mirror["status"] != "READY":
        warnings.append(f"ALGORITHM_SOURCE_NOT_SYNCED: {item['source_id']} ({mirror['status']})")
        return result, warnings
    index = _load_mirror_index(_algorithm_index_root(workspace_root, source))
    if index is None:
        result["status"] = "STALE"
        warnings.append(f"ALGORITHM_SOURCE_INDEX_MISSING: {item['source_id']}")
        return result, warnings
    files = {str(row.get("path")): row for row in index["files"] if isinstance(row, dict) and row.get("path")}
    for entry in item.get("entry_points", []):
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path", ""))
        file_row = files.get(path)
        local_entry = {**entry, "local_path": f"{mirror['mirror_path']}/{path}"}
        if file_row is None:
            local_entry["status"] = "MISSING"
        elif str(file_row.get("sha256", "")).lower() != str(entry.get("file_sha256", "")).lower():
            local_entry["status"] = "STALE"
        else:
            local_entry["status"] = "READY"
            symbols = file_row.get("symbols") if isinstance(file_row.get("symbols"), list) else []
            match = next((symbol for symbol in symbols if symbol.get("symbol") == entry.get("symbol")), None)
            if match:
                local_entry["line"] = match.get("line")
        result["entry_points"].append(local_entry)
    return result, warnings


def _search_local_mirror(workspace_root: Path, source: dict[str, Any], query: str, limit: int = MIRROR_QUERY_LIMIT) -> list[dict[str, Any]]:
    mirror = _mirror_status(workspace_root, source)
    if mirror["status"] != "READY":
        return []
    index = _load_mirror_index(_algorithm_index_root(workspace_root, source))
    if index is None:
        return []
    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    mirror_path = _algorithm_mirror_path(workspace_root, source)
    for row in index.get("files", []):
        if len(matches) >= limit or not isinstance(row, dict) or row.get("text_readable") is not True:
            continue
        path = str(row.get("path", ""))
        source_file = mirror_path / path
        try:
            lines = source_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            if needle in line.casefold():
                matches.append({
                    "path": f"{mirror['mirror_path']}/{path}",
                    "line": line_number,
                    "snippet": line.strip()[:240],
                })
                if len(matches) >= limit:
                    break
    return matches


def lookup(
    workspace_root: Path,
    tags: list[str],
    limit: int = 5,
    layer: str = "all",
    query: str = "",
) -> dict[str, Any]:
    if not tags or limit < 1:
        raise ValueError("lookup requires at least one tag")
    if layer not in LAYERS:
        raise ValueError(f"lookup layer must be one of: {', '.join(LAYERS)}")
    wanted = {tag.strip().lower() for tag in tags if tag.strip()}
    ranked: list[tuple[int, int, str, dict[str, Any]]] = []
    issues: list[str] = []
    algorithm_sources = _algorithm_source_map(workspace_root)
    item_sets: list[tuple[str, list[dict[str, Any]], str]] = []
    if layer in {"card", "all"}:
        records, record_issues = card_records(workspace_root)
        item_sets.append(("card", records, "card_id"))
        issues.extend(record_issues)
    if layer in {"module", "all"}:
        records, record_issues = module_records(workspace_root)
        item_sets.append(("module", records, "module_id"))
        issues.extend(record_issues)
    if layer in {"playbook", "all"}:
        records, record_issues = playbook_records(workspace_root)
        item_sets.append(("playbook", records, "playbook_id"))
        issues.extend(record_issues)
    if layer in {"code", "all"}:
        records, record_issues = algorithm_records(workspace_root)
        item_sets.append(("code", records, "algorithm_card_id"))
        issues.extend(record_issues)

    kind_priority = {"module": 0, "playbook": 1, "code": 2, "card": 3}
    for kind, records, identity_key in item_sets:
        for item in records:
            matched = sorted(wanted & set(item["tags"]))
            if matched:
                ranked.append((len(matched), kind_priority[kind], str(item[identity_key]), {**item, "kind": kind, "identity_key": identity_key}))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    results: list[dict[str, Any]] = []
    for score, _priority, _identity, item in ranked[:limit]:
        identity_key = item["identity_key"]
        row = {
            "kind": item["kind"],
            "item_id": item[identity_key],
            identity_key: item[identity_key],
            "path": item["path"].relative_to(library_root(workspace_root)).as_posix(),
            "score": score,
            "matched_tags": sorted(wanted & set(item["tags"])),
            "stage_scope": item.get("stage_scope", list(EARLY_STAGES)),
            "preview": re.sub(r"\s+", " ", item["body"].strip())[:320],
            "valid": item["valid"],
            "contest_evidence_eligible": False,
        }
        if item["kind"] == "card":
            row.update({
                "source_id": item["source_id"],
                "pdf_page": item["pdf_page"],
                "printed_page": item["printed_page"],
                "locator_confidence": item["locator_confidence"],
            })
        elif item["kind"] == "module":
            row["source_cards"] = item["source_cards"]
        elif item["kind"] == "playbook":
            row["modules"] = item["modules"]
        else:
            source = algorithm_sources.get(str(item["source_id"]))
            local_data, local_warnings = _local_entry_points(workspace_root, item, source)
            issues.extend(local_warnings)
            file_matches = _search_local_mirror(workspace_root, source, query) if source and query else []
            row.update({
                "source_id": item["source_id"],
                "source_commit": item["source_commit"],
                "source_path": item["source_path"],
                "language": item["language"],
                "license_status": item["license_status"],
                "interface": item["interface"],
                "baseline_required": item["baseline_required"],
                "baseline_options": item["baseline_options"],
                "known_risks": item["known_risks"],
                "adaptation_required": item["adaptation_required"],
                "local_mirror": local_data["mirror_path"],
                "mirror_status": local_data["status"],
                "entry_points": local_data["entry_points"],
                "file_matches": file_matches,
                "skeleton_path": item["skeleton_path"],
            })
        results.append(row)
    return {
        "schema_version": 1,
        "layer": layer,
        "tags": sorted(wanted),
        "results": results,
        "warnings": sorted(set(issues)),
    }


def status(workspace_root: Path) -> dict[str, Any]:
    sources = load_sources(workspace_root)
    records, card_issues = card_records(workspace_root)
    modules, module_issues = module_records(workspace_root)
    playbooks, playbook_issues = playbook_records(workspace_root)
    algorithms, algorithm_issues = algorithm_records(workspace_root)
    coverage = {
        tag: {
            "cards": sum(tag in record["tags"] and record["valid"] for record in records),
            "modules": sum(tag in record["tags"] and record["valid"] for record in modules),
            "playbooks": sum(tag in record["tags"] and record["valid"] for record in playbooks),
        }
        for tag in CORE_TAGS
    }
    verification = verify(workspace_root)
    source_status = {row["source_id"]: row["status"] for row in verification["sources"]}
    for record in records:
        if source_status.get(record["source_id"]) == "HASH_MISMATCH":
            record["status"] = "STALE"
    card_status = {item["card_id"]: item.get("status", "READY" if item["valid"] else "INVALID") for item in records}
    for module in modules:
        if not module["valid"]:
            module["status"] = "INVALID"
        elif any(card_status.get(card_id) == "STALE" for card_id in module["source_cards"]):
            module["status"] = "STALE"
        else:
            module["status"] = "READY"
    module_status = {item["module_id"]: item["status"] for item in modules}
    for playbook in playbooks:
        if not playbook["valid"]:
            playbook["status"] = "INVALID"
        elif any(module_status.get(module_id) == "STALE" for module_id in playbook["modules"]):
            playbook["status"] = "STALE"
        else:
            playbook["status"] = "READY"
    passed = not card_issues and not module_issues and not playbook_issues and not algorithm_issues and verification["passed"]
    try:
        algorithm_sources_payload = load_algorithm_sources(workspace_root)
        algorithm_source_count = len(algorithm_sources_payload["sources"])
    except FileNotFoundError:
        algorithm_sources_payload = {"sources": []}
        algorithm_source_count = 0
    mirror_reports = []
    for source in algorithm_sources_payload.get("sources", []):
        mirror = _mirror_status(workspace_root, source)
        state_path = _algorithm_index_root(workspace_root, source) / "mirror_state.json"
        state_payload: dict[str, Any] = {}
        if state_path.is_file():
            try:
                loaded = json.loads(state_path.read_text(encoding="utf-8"))
                state_payload = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                state_payload = {}
        mirror_reports.append({
            "source_id": source["source_id"],
            **mirror,
            "head_verified": state_payload.get("head_verified", False),
            "synced_at": state_payload.get("synced_at"),
            "license_status": state_payload.get("license_status", source.get("license_status", "UNKNOWN")),
            "license_files": state_payload.get("license_files", []),
            "indexed_file_count": state_payload.get("file_count", 0),
        })
    return {
        "schema_version": 1,
        "passed": passed,
        "source_count": len(sources["sources"]),
        "card_count": len(records),
        "valid_card_count": sum(item["valid"] for item in records),
        "module_count": len(modules),
        "valid_module_count": sum(item["valid"] for item in modules),
        "playbook_count": len(playbooks),
        "valid_playbook_count": sum(item["valid"] for item in playbooks),
        "algorithm_source_count": algorithm_source_count,
        "algorithm_card_count": len(algorithms),
        "valid_algorithm_card_count": sum(item["valid"] for item in algorithms),
        "coverage": coverage,
        "card_issues": card_issues,
        "module_issues": sorted(set(module_issues) - set(card_issues)),
        "playbook_issues": sorted(set(playbook_issues) - set(module_issues)),
        "cards": [
            {"card_id": item["card_id"], "source_id": item["source_id"], "status": item.get("status", "READY")}
            for item in records
        ],
        "modules": [
            {"module_id": item["module_id"], "source_cards": item["source_cards"], "status": item["status"]}
            for item in modules
        ],
        "playbooks": [
            {"playbook_id": item["playbook_id"], "modules": item["modules"], "status": item["status"]}
            for item in playbooks
        ],
        "algorithm_issues": sorted(set(algorithm_issues)),
        "algorithm_cards": [
            {
                "algorithm_card_id": item["algorithm_card_id"],
                "source_id": item["source_id"],
                "status": "READY" if item["valid"] else "INVALID",
                "entrypoint_count": len(item.get("entry_points", [])),
                "skeleton_path": item.get("skeleton_path", ""),
            }
            for item in algorithms
        ],
        "algorithm_mirrors": mirror_reports,
        "pdf_verification": verification,
    }


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only competition knowledge library")
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("verify")
    lookup_parser = sub.add_parser("lookup")
    lookup_parser.add_argument("--tags", required=True)
    lookup_parser.add_argument("--limit", type=int, default=5)
    lookup_parser.add_argument("--layer", choices=LAYERS, default="all")
    lookup_parser.add_argument("--query", default="")
    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--source", required=True)
    sub.add_parser("status")
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    try:
        if args.action == "verify":
            result = verify(root)
        elif args.action == "lookup":
            result = lookup(
                root,
                [item.strip() for item in args.tags.split(",")],
                args.limit,
                args.layer,
                args.query,
            )
        elif args.action == "sync":
            result = sync_algorithm_source(root, args.source)
        else:
            result = status(root)
    except Exception as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
