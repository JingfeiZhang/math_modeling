from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def output_map(report: dict) -> dict[str, str]:
    return {item["path"]: item["sha256"] for item in report["outputs"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = []
    for recipe_root in sorted(path for path in args.root.iterdir() if (path / "run_report.json").is_file()):
        before = json.loads((recipe_root / "run_report.json").read_text(encoding="utf-8"))
        completed = subprocess.run(
            [sys.executable, "run.py"],
            cwd=recipe_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        after = json.loads((recipe_root / "run_report.json").read_text(encoding="utf-8"))
        same_outputs = output_map(before) == output_map(after)
        same_metrics = before["metrics"] == after["metrics"]
        records.append(
            {
                "recipe_id": recipe_root.name,
                "returncode": completed.returncode,
                "same_seed": before["seed"] == after["seed"],
                "same_metrics": same_metrics,
                "same_output_hashes": same_outputs,
                "status": "passed" if completed.returncode == 0 and same_metrics and same_outputs else "failed",
            }
        )
    report = {
        "schema_version": 1,
        "recipe_count": len(records),
        "passed": sum(item["status"] == "passed" for item in records),
        "failed": sum(item["status"] == "failed" for item in records),
        "records": records,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("recipe_count", "passed", "failed")}, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
