from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = []
    for recipe_root in sorted(path for path in args.root.iterdir() if (path / "recipe.json").is_file()):
        before = {path.relative_to(recipe_root).as_posix() for path in recipe_root.rglob("*") if path.is_file()}
        completed = subprocess.run(
            [sys.executable, "run.py"],
            cwd=recipe_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
        report_path = recipe_root / "run_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
        after = {path.relative_to(recipe_root).as_posix() for path in recipe_root.rglob("*") if path.is_file()}
        required = {"results.json", "series.csv", "figure.png", "figure.svg", "figure.pdf", "run_report.json"}
        records.append(
            {
                "recipe_id": recipe_root.name,
                "returncode": completed.returncode,
                "status": "passed" if completed.returncode == 0 and report and required <= after else "failed",
                "new_files": sorted(after - before),
                "required_outputs_present": sorted(required & after),
                "run_report_sha256": sha256(report_path) if report_path.is_file() else None,
                "stdout": completed.stdout.strip()[-1000:],
                "stderr": completed.stderr.strip()[-1000:],
            }
        )

    summary = {
        "schema_version": 1,
        "python": sys.executable,
        "recipe_count": len(records),
        "passed": sum(item["status"] == "passed" for item in records),
        "failed": sum(item["status"] == "failed" for item in records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("recipe_count", "passed", "failed")}, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
