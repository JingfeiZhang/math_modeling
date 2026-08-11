"""Inspect and normalize the shared modeling workbench layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROLE_DIRS: dict[str, tuple[str, ...]] = {
    "shared": ("config", "templates", "corpus", "src", "scripts", "matlab"),
    "projects": ("projects",),
    "legacy_demo": ("paper", "problems", "experiments", "results", "figures"),
    "reports": ("reports",),
    "tooling": ("tools", ".tools", ".audit", "skill_staging", "tmp"),
    "generated": ("output",),
}


def inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stats(path: Path) -> dict[str, Any]:
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file() and not item.is_symlink()] if path.is_dir() else []
    total = sum(item.stat().st_size for item in files)
    latest = max((item.stat().st_mtime for item in files), default=path.stat().st_mtime if path.exists() else 0)
    return {
        "exists": path.exists(),
        "files": len(files),
        "bytes": total,
        "megabytes": round(total / 1024 / 1024, 3),
        "latest_mtime_utc": datetime.fromtimestamp(latest, UTC).isoformat() if latest else None,
    }


def output_candidates(root: Path) -> list[tuple[Path, Path, str]]:
    output = root / "output"
    candidates: list[tuple[Path, Path, str]] = []

    def add(source: Path, destination: Path, rule: str) -> None:
        if source.exists() and inside(root, source) and inside(root, destination):
            candidates.append((source, destination, rule))

    if output.exists():
        for source in sorted(output.glob("pytest-*")):
            add(source, output / "_verification" / "pytest" / source.name, "pytest-directories")
        add(output / "template-validation", output / "_verification" / "templates" / "template-validation", "template-validation")
        add(output / "rendered-pages", output / "_verification" / "pdf" / "rendered-pages", "rendered-pages")
        add(output / "pdf-visual-pages", output / "_verification" / "pdf" / "pdf-visual-pages", "pdf-visual-pages")
        for source in sorted(output.glob("matlab-*")):
            add(source, output / "_demos" / "matlab" / source.name, "matlab-demos")
        add(output / "matlab_figures", output / "_demos" / "matlab" / "matlab_figures", "matlab-figures")
        add(output / "originlab-mcp-smoke", output / "_demos" / "originlab" / "originlab-mcp-smoke", "originlab-smoke")
        for source in sorted(output.glob("tmp*")):
            add(source, output / "_archive" / "temporary" / source.name, "temporary-directories")
        conda_tmp = output / ".conda-tmp"
        if conda_tmp.is_dir() and any(conda_tmp.iterdir()):
            add(conda_tmp, output / "_archive" / "temporary" / ".conda-tmp", "conda-temporary")
        for source in sorted(output.glob("extended-smoke-*.json")):
            add(source, output / "_verification" / "environment" / source.name, "environment-smoke-reports")
    add(root / "report.log", output / "_archive" / "legacy-root" / "report.log", "legacy-report-log")
    return candidates


def collision_free_destination(source: Path, destination: Path) -> Path:
    if not destination.exists():
        return destination
    suffix = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:8]
    return destination.with_name(f"{destination.name}-duplicate-{suffix}")


def plan_payload(root: Path) -> list[dict[str, str]]:
    return [{
        "rule": rule,
        "source": source.relative_to(root).as_posix(),
        "destination": destination.relative_to(root).as_posix(),
    } for source, destination, rule in output_candidates(root)]


def inspect(root: Path, output_path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "layout_id": "modeling-workbench-v1",
        "root": str(root.resolve()),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "roles": {},
        "migration_candidates": plan_payload(root),
    }
    for role, entries in ROLE_DIRS.items():
        payload["roles"][role] = {relative: stats(root / relative) for relative in entries}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def normalize(root: Path) -> dict[str, Any]:
    migration_id = datetime.now(UTC).strftime("layout-migration-%Y%m%dT%H%M%S%fZ")
    migration_root = root / "output" / "_archive" / migration_id
    entries: list[dict[str, Any]] = []
    for source, destination, rule in output_candidates(root):
        if not inside(root, source) or not inside(root, destination):
            raise ValueError(f"Refusing path outside workspace: {source} -> {destination}")
        final_destination = collision_free_destination(source, destination)
        final_destination.parent.mkdir(parents=True, exist_ok=True)
        before = stats(source)
        source_hash = file_hash(source) if source.is_file() else None
        shutil.move(str(source), str(final_destination))
        entries.append({
            "rule": rule,
            "source": source.relative_to(root).as_posix(),
            "destination": final_destination.relative_to(root).as_posix(),
            "before": before,
            "after": stats(final_destination),
            "source_sha256": source_hash,
        })
    manifest = {
        "schema_version": 1,
        "migration_id": migration_id,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "root": str(root.resolve()),
        "moved": entries,
        "moved_count": len(entries),
        "no_delete_policy": True,
    }
    migration_root.mkdir(parents=True, exist_ok=True)
    (migration_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    for role, entries in ROLE_DIRS.items():
        for relative in entries:
            check(f"role:{role}:{relative}", (root / relative).exists(), str(root / relative))
    projects_root = (root / "projects").resolve()
    registry_path = root / "config" / "projects.json"
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for item in registry.get("projects", []):
            project_root = (root / str(item["root"])).resolve()
            check(f"project:{item['id']}:inside-projects", inside(projects_root, project_root), str(project_root))
            contest = project_root / "contest.yaml"
            problem = ""
            if contest.is_file():
                for line in contest.read_text(encoding="utf-8").splitlines():
                    if line.startswith("problem:"):
                        problem = line.split(":", 1)[1].strip().strip("\"'")
                        break
            if problem == "TBD":
                check(f"project:{item['id']}:precontest-state-absent", not (project_root / "state" / "decision_log.json").exists())
                check(f"project:{item['id']}:precontest-figure-contract-absent", not (project_root / "paper" / "figure_contracts.yaml").exists())
    contest = root / "contest.yaml"
    check("legacy-root-contest-is-tbd", "problem: TBD" in contest.read_text(encoding="utf-8") if contest.is_file() else False)
    return {"schema_version": 1, "passed": all(item["passed"] for item in checks), "checks": checks, "generated_at_utc": datetime.now(UTC).isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--action", choices=("inspect", "preview", "normalize", "verify"), required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"workspace root does not exist: {root}")
    if args.action == "inspect":
        payload = inspect(root, root / "output" / "workspace_inventory.json")
    elif args.action == "preview":
        moves = plan_payload(root)
        payload = {"schema_version": 1, "root": str(root), "moves": moves, "move_count": len(moves)}
    elif args.action == "normalize":
        payload = normalize(root)
    else:
        payload = verify(root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
