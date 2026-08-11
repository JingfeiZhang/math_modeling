#!/usr/bin/env python3
"""Seal and verify the final CUMCM paper/support artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


AUDIT_REPORTS = (
    "paper_audit.json",
    "figure_audit.json",
    "figure_style_audit.json",
    "pdf_visual_audit.json",
    "code_parity_audit.json",
    "ai_usage_audit.json",
    "package_audit.json",
    "audit.json",
)


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def dump_yaml(path: Path, value: dict) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def digest(path: Path) -> dict:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return {
        "path": path.as_posix(),
        "bytes": path.stat().st_size,
        "md5": md5.hexdigest(),
        "sha256": sha256.hexdigest(),
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
    }


def relative_digest(root: Path, path: Path) -> dict:
    value = digest(path)
    value["path"] = path.resolve().relative_to(root.resolve()).as_posix()
    return value


def report_passed(path: Path) -> bool:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return value.get("passed", value.get("status") == "PASS") is True


def manifest_path(root: Path, contest: dict) -> Path:
    configured = contest.get("submission", {}).get("release_manifest", "output/release/release_manifest.json")
    return (root / configured).resolve()


def publish_path(root: Path, contest: dict) -> Path:
    configured = contest.get("submission", {}).get("publish_dir", "submission")
    target = (root / configured).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("submission publish directory must stay inside the project root") from exc
    return target


def verify(root: Path, manifest: Path, require_confirmations: bool = False) -> dict:
    if not manifest.is_file():
        return {"schema_version": 1, "status": "FAIL", "passed": False, "errors": [f"release manifest is missing: {manifest}"]}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks: list[dict] = []
    for expected in payload.get("artifacts", []):
        path = (root / expected.get("path", "")).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            errors.append(f"release artifact escapes workspace: {expected.get('path')}")
            continue
        if not path.is_file():
            errors.append(f"release artifact is missing: {expected.get('path')}")
            continue
        observed = relative_digest(root, path)
        passed = all(observed.get(key) == expected.get(key) for key in ("bytes", "md5", "sha256"))
        checks.append({"path": expected.get("path"), "passed": passed, "expected_md5": expected.get("md5"), "observed_md5": observed.get("md5")})
        if not passed:
            errors.append(f"release artifact changed after sealing: {expected.get('path')}")
    for expected in payload.get("audit_evidence", []):
        path = (root / expected.get("path", "")).resolve()
        if not path.is_file() or relative_digest(root, path)["sha256"] != expected.get("sha256"):
            errors.append(f"audit evidence changed after sealing: {expected.get('path')}")
    if require_confirmations:
        checklist_path = (root / payload.get("checklist", "")).resolve()
        checklist = load_yaml(checklist_path) if checklist_path.is_file() else {}
        missing = [key for key, value in checklist.get("confirmations", {}).items() if value is not True]
        if missing:
            errors.append("manual submission confirmations are incomplete: " + ", ".join(missing))
    return {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "passed": not errors,
        "manifest": manifest.resolve().relative_to(root.resolve()).as_posix(),
        "checks": checks,
        "errors": errors,
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }


def seal(root: Path, workspace_root: Path | None = None) -> dict:
    contest = load_yaml(root / "contest.yaml")
    if str(contest.get("problem", "TBD")).upper() == "TBD":
        raise ValueError("submission sealing is forbidden before a real problem is initialized")
    output = root / "output"
    paper = root / contest.get("paths", {}).get("paper_pdf", "output/submission.pdf")
    support = root / contest.get("paths", {}).get("support_zip", "output/supporting.zip")
    for path in (paper, support):
        if not path.is_file():
            raise FileNotFoundError(f"release artifact is missing: {path}")
    failed_reports = [name for name in AUDIT_REPORTS if not report_passed(output / name)]
    if failed_reports:
        raise ValueError("submission cannot be sealed; audit reports are missing or failed: " + ", ".join(failed_reports))
    release_manifest = manifest_path(root, contest)
    if release_manifest.is_file():
        current = verify(root, release_manifest)
        if current["passed"]:
            current["status"] = "ALREADY_SEALED"
            return current
        raise ValueError("an existing release seal is invalid; archive it before creating a new release")

    submission = contest.get("submission", {})
    release_dir = release_manifest.parent
    release_dir.mkdir(parents=True, exist_ok=True)
    paper_filename = str(submission.get("paper_filename", paper.name))
    support_filename = str(submission.get("support_filename", support.name))
    if Path(paper_filename).name != paper_filename or Path(support_filename).name != support_filename:
        raise ValueError("configured release filenames must be simple file names")
    publish_dir = publish_path(root, contest)
    publish_dir.mkdir(parents=True, exist_ok=True)
    allowed_publish_names = {paper_filename, support_filename}
    unexpected = sorted(path.name for path in publish_dir.iterdir() if path.name not in allowed_publish_names)
    if unexpected:
        raise ValueError("submission publish directory contains unexpected entries: " + ", ".join(unexpected))
    release_paper = publish_dir / paper_filename
    release_support = publish_dir / support_filename
    shutil.copy2(paper, release_paper)
    shutil.copy2(support, release_support)
    checklist_path = (root / submission.get("release_checklist", "output/release/submission_checklist.yaml")).resolve()
    template = root / "templates" / "submission" / "release_checklist.yaml"
    if not template.is_file() and workspace_root is not None:
        template = workspace_root / "templates" / "submission" / "release_checklist.yaml"
    checklist = load_yaml(template) if template.is_file() else {"schema_version": 1, "confirmations": {}}
    checklist.update({
        "competition": contest.get("competition"),
        "year": contest.get("year"),
        "problem": contest.get("problem"),
        "hash_deadline": submission.get("hash_deadline"),
        "upload_start": submission.get("upload_start"),
        "upload_deadline": submission.get("upload_deadline"),
        "operator_role": submission.get("operator_role", "first_registered_student"),
    })
    dump_yaml(checklist_path, checklist)

    artifacts = [relative_digest(root, release_paper), relative_digest(root, release_support)]
    audit_evidence = [relative_digest(root, output / name) for name in AUDIT_REPORTS]
    payload = {
        "schema_version": 1,
        "status": "SEALED",
        "competition": contest.get("competition"),
        "year": contest.get("year"),
        "problem": contest.get("problem"),
        "sealed_at_utc": datetime.now(UTC).isoformat(),
        "hash_deadline": submission.get("hash_deadline"),
        "upload_window": {"start": submission.get("upload_start"), "end": submission.get("upload_deadline")},
        "operator_role": submission.get("operator_role", "first_registered_student"),
        "artifacts": artifacts,
        "audit_evidence": audit_evidence,
        "checklist": checklist_path.relative_to(root).as_posix(),
        "publish_dir": publish_dir.relative_to(root).as_posix(),
    }
    temporary = release_manifest.with_suffix(release_manifest.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(release_manifest)
    (release_dir / "md5sums.txt").write_text("".join(f"{item['md5']}  {Path(item['path']).name}\n" for item in artifacts), encoding="utf-8")
    (release_dir / "sha256sums.txt").write_text("".join(f"{item['sha256']}  {Path(item['path']).name}\n" for item in artifacts), encoding="utf-8")
    return {"schema_version": 1, "status": "SEALED", "passed": True, "manifest": release_manifest.relative_to(root).as_posix(), "artifacts": artifacts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--action", choices=("seal", "verify"), required=True)
    parser.add_argument("--require-confirmations", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        contest = load_yaml(root / "contest.yaml")
        workspace_root = args.workspace_root.resolve() if args.workspace_root else root
        result = seal(root, workspace_root) if args.action == "seal" else verify(root, manifest_path(root, contest), args.require_confirmations)
    except Exception as exc:
        result = {"schema_version": 1, "status": "FAIL", "passed": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
