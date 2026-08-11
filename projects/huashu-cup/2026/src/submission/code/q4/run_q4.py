#!/usr/bin/env python
"""Run the bounded 72-hour Q4 joint task-storage optimization."""

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACKAGE_ROOT))

from code.common.runtime import ensure_inputs
from code.q4 import joint_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Q4 joint optimization.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument("--q2-schedule", type=Path, default=None)
    args = parser.parse_args(argv)
    ensure_inputs("Q4", args.input_dir)
    os.environ["PYTHONHASHSEED"] = str(args.seed)
    q2_schedule = args.q2_schedule or args.input_dir / "q2_full_candidate_schedule.csv"
    if not q2_schedule.is_file():
        raise FileNotFoundError("Q4 requires q2_full_candidate_schedule.csv from the Q2 runner")
    return joint_core.main(["--input-dir", str(args.input_dir), "--output-dir", str(args.output_dir), "--q2-schedule", str(q2_schedule), "--seed", str(args.seed)])


if __name__ == "__main__":
    raise SystemExit(main())
