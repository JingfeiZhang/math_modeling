#!/usr/bin/env python3
"""Verify paper-declared code against project sources and the support ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


LISTING_RE = re.compile(
    r"\\(?:lstinputlisting|verbatiminput)\s*(?:\[[^]]*\])?\s*\{([^{}]+)\}"
    r"|\\inputminted\s*(?:\[[^]]*\])?\s*\{[^{}]+\}\s*\{([^{}]+)\}",
    re.I,
)
APPENDIX_RANGE_RE = re.compile(
    r"\\AppendixCodeRange\s*\{([^{}]+)\}\s*\{[^{}]*\}\s*\{[^{}]*\}\s*\{[^{}]+\}",
    re.I,
)
CODE_SUFFIXES = {".py", ".m", ".r", ".rmd", ".jl", ".cpp", ".c", ".h", ".java", ".ps1", ".sh", ".ipynb"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def expand_tex(paper_dir: Path) -> dict[Path, str]:
    include_re = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
    files: dict[Path, str] = {}
    entry = paper_dir / "main.tex"

    def visit(path: Path, stack: tuple[Path, ...]) -> None:
        path = path.resolve()
        if path in stack or not path.is_file() or path in files:
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        files[path] = text
        for raw in include_re.findall(text):
            candidate = (path.parent / raw.strip()).resolve()
            if not candidate.suffix:
                candidate = candidate.with_suffix(".tex")
            visit(candidate, (*stack, path))

    visit(entry, ())
    return files


def relative_project_file(root: Path, candidate: Path) -> tuple[str | None, bool]:
    try:
        relative = candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None, False
    return relative, candidate.is_file() and candidate.suffix.lower() in CODE_SUFFIXES


def resolve_code_path(root: Path, paper_dir: Path, owner: Path, raw: str) -> Path | None:
    value = raw.strip()
    if value.startswith(r"\SubmissionSourceRoot/"):
        value = "src/submission/" + value.split("/", 1)[1]
    elif value == r"\SubmissionSourceRoot":
        value = "src/submission"
    else:
        value = value.replace("\\", "/")
    candidates = [(owner.parent / value).resolve(), (paper_dir / value).resolve(), (root / value).resolve()]
    for candidate in candidates:
        relative, valid = relative_project_file(root, candidate)
        if relative is not None and valid:
            return candidate
    return None


def referenced_code(root: Path, paper_dir: Path) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for owner, text in expand_tex(paper_dir).items():
        try:
            owner_relative = owner.relative_to(root).as_posix()
        except ValueError:
            owner_relative = str(owner)
        raw_references = [
            match.group(1) or match.group(2) or ""
            for match in LISTING_RE.finditer(text)
            if "#" not in (match.group(1) or match.group(2) or "")
        ]
        raw_references.extend(match.group(1) for match in APPENDIX_RANGE_RE.finditer(text))
        for raw in raw_references:
            path = resolve_code_path(root, paper_dir, owner, raw)
            relative = path.relative_to(root).as_posix() if path else None
            references.append(
                {
                    "origin": "latex",
                    "owner": owner_relative,
                    "reference": raw.strip(),
                    "path": relative,
                    "support_path": relative,
                    "exists": path is not None,
                    "sha256": sha256_bytes(path.read_bytes()) if path else None,
                }
            )
    return references


def valid_support_path(raw: str) -> str | None:
    value = raw.strip().replace("\\", "/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts:
        return None
    return path.as_posix()


def manifest_code(root: Path, paper_dir: Path) -> tuple[list[dict[str, Any]], bool]:
    manifest_path = paper_dir / "code_manifest.yaml"
    if not manifest_path.is_file():
        return [], False
    entries = load_yaml(manifest_path).get("files", [])
    result: list[dict[str, Any]] = []
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict):
            raw = str(entry.get("path", ""))
            raw_support = str(entry.get("support_path", raw))
        else:
            raw = str(entry)
            raw_support = raw
        candidate = (root / raw).resolve()
        relative, exists = relative_project_file(root, candidate)
        result.append(
            {
                "origin": "manifest",
                "path": relative,
                "declared": raw,
                "support_path": valid_support_path(raw_support),
                "exists": exists,
                "sha256": sha256_bytes(candidate.read_bytes()) if exists else None,
            }
        )
    return result, True


def support_members(path: Path) -> tuple[dict[str, bytes], list[dict[str, str]], bool]:
    errors: list[dict[str, str]] = []
    if not path.is_file():
        return {}, [{"code": "SUPPORT_ARCHIVE_MISSING", "message": f"supporting ZIP is missing: {path}"}], False
    if path.suffix.lower() != ".zip":
        return {}, [{"code": "SUPPORT_ARCHIVE_TYPE", "message": f"supporting archive is not ZIP: {path}"}], False
    members: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                name = valid_support_path(member.filename)
                if name is None:
                    errors.append({"code": "SUPPORT_MEMBER_PATH", "message": f"invalid supporting ZIP member path: {member.filename}"})
                    continue
                if name in members:
                    errors.append({"code": "SUPPORT_DUPLICATE_MEMBER", "message": f"duplicate supporting ZIP member: {name}"})
                    continue
                members[name] = archive.read(member)
    except (OSError, zipfile.BadZipFile) as exc:
        return {}, [{"code": "SUPPORT_ARCHIVE_INVALID", "message": f"cannot read supporting ZIP {path}: {exc}"}], False
    return members, errors, True


def audit(root: Path, paper_dir: Path, support: Path, check_support: bool = True) -> dict:
    contest = load_yaml(root / "contest.yaml")
    formal = str(contest.get("problem", "TBD")).upper() != "TBD"
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    references = referenced_code(root, paper_dir)
    declared, manifest_exists = manifest_code(root, paper_dir)
    if formal and not manifest_exists:
        errors.append({"code": "CODE_MANIFEST_MISSING", "message": "paper/code_manifest.yaml is missing"})
    if not references and not declared:
        finding = {"code": "CODE_APPENDIX_MISSING", "message": "no LaTeX code listing or paper/code_manifest.yaml entry was found"}
        (errors if formal else warnings).append(finding)

    manifest_by_path: dict[str, dict[str, Any]] = {}
    for item in declared:
        path = item.get("path")
        if not path:
            errors.append({"code": "CODE_SOURCE_MISSING", "message": f"code source does not exist or is invalid: {item.get('declared')}"})
            continue
        if item.get("support_path") is None:
            errors.append({"code": "CODE_SUPPORT_PATH_INVALID", "message": f"invalid support path for code source: {item.get('declared')}"})
            continue
        previous = manifest_by_path.get(path)
        if previous and previous.get("support_path") != item.get("support_path"):
            errors.append({"code": "CODE_MANIFEST_CONFLICT", "message": f"conflicting support paths for code source: {path}"})
            continue
        manifest_by_path[path] = item

    for item in references:
        path = item.get("path")
        if not path:
            errors.append({"code": "CODE_REFERENCE_UNRESOLVED", "message": f"cannot resolve LaTeX code reference: {item.get('reference')}", "owner": item.get("owner")})
            continue
        declared_item = manifest_by_path.get(path)
        if declared_item:
            item["support_path"] = declared_item["support_path"]
        elif formal:
            errors.append({"code": "CODE_LISTING_NOT_DECLARED", "message": f"LaTeX code listing is absent from paper/code_manifest.yaml: {path}"})

    combined: dict[str, dict[str, Any]] = {}
    for item in [*declared, *references]:
        path = item.get("path")
        if not path:
            continue
        support_path = item.get("support_path")
        if support_path is None:
            continue
        key = f"{path}\0{support_path}"
        current = combined.setdefault(
            key,
            {
                "path": path,
                "support_path": support_path,
                "exists": bool(item.get("exists")),
                "sha256": item.get("sha256"),
                "origins": [],
            },
        )
        current["origins"].append(item["origin"])
        if current.get("sha256") != item.get("sha256"):
            errors.append({"code": "CODE_SOURCE_HASH_CONFLICT", "message": f"project source hash changed while auditing: {path}"})

    members: dict[str, bytes] = {}
    support_checked = False
    if check_support:
        members, support_errors, support_checked = support_members(support)
        errors.extend(support_errors)

    if check_support and support_checked:
        for item in combined.values():
            support_path = item["support_path"]
            payload = members.get(support_path)
            if payload is None:
                errors.append({"code": "CODE_NOT_IN_SUPPORT", "message": f"paper code is absent from supporting ZIP: {support_path}", "source_path": item["path"]})
                continue
            support_hash = sha256_bytes(payload)
            if item.get("sha256") != support_hash:
                errors.append(
                    {
                        "code": "CODE_HASH_MISMATCH",
                        "message": f"project/support code hash differs: {item['path']} -> {support_path}",
                        "paper_sha256": item.get("sha256"),
                        "support_sha256": support_hash,
                    }
                )

    result = {
        "schema_version": 2,
        "formal": formal,
        "support_requested": check_support,
        "support_checked": support_checked,
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "manifest_code_entries": len(declared),
            "latex_code_listings": len(references),
            "paper_code_entries": len(combined),
            "support_entries": len(members),
        },
        "entries": list(combined.values()),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--paper-dir", type=Path, default=Path("paper"))
    parser.add_argument("--support", type=Path, default=Path("output/supporting.zip"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-support", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = audit(root, (root / args.paper_dir).resolve(), (root / args.support).resolve(), check_support=not args.skip_support)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
