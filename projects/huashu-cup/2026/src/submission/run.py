#!/usr/bin/env python
"""Unified entry point for the HuaShu Cup C-question source package."""

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from code.common.runtime import verification_payload, write_json

RUNNERS = {
    "Q1": ROOT / "code/q1/run_q1.py",
    "Q2": ROOT / "code/q2/run_q2.py",
    "Q3": ROOT / "code/q3/run_q3.py",
    "Q4": ROOT / "code/q4/run_q4.py",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or validate the four formal models for problem C."
    )
    parser.add_argument(
        "--question", default="all", choices=["Q1", "Q2", "Q3", "Q4", "all"]
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("verify_output"))
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.question == "all":
        questions = list(RUNNERS)
    elif args.question == "Q4":
        # Q4 is defined on a Q2 schedule; direct Q4 runs create the
        # prerequisite in a private sibling directory.
        questions = ["Q2", "Q4"]
    else:
        questions = [args.question]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.verify_only:
        payloads = [verification_payload(question, args.input_dir) for question in questions]
        payload = {
            "status": "PASS",
            "mode": "verify-only",
            "questions": payloads,
        }
        write_json(args.output_dir / "input_verification.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = str(args.seed)
    for question in questions:
        if args.question == "all":
            question_output = args.output_dir / question
        elif args.question == "Q4" and question == "Q2":
            question_output = args.output_dir / "_q2_prerequisite"
        else:
            question_output = args.output_dir
        command = [
            sys.executable,
            str(RUNNERS[question]),
            "--input-dir",
            str(args.input_dir.resolve()),
            "--output-dir",
            str(question_output.resolve()),
            "--seed",
            str(args.seed),
        ]
        if question == "Q4":
            q2_root = args.output_dir / "Q2" if args.question == "all" else args.output_dir / "_q2_prerequisite"
            command.extend(
                ["--q2-schedule", str((q2_root / "q2_full_candidate_schedule.csv").resolve())]
            )
        completed = subprocess.run(command, check=False, env=environment)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
