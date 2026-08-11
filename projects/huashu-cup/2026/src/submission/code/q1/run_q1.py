#!/usr/bin/env python
"""Run the Q1 forecast and scheduling models with the same contest inputs."""

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
from code.q1 import forecast_core, schedule_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Q1 forecast and CP-SAT scheduling.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260801)
    args = parser.parse_args(argv)
    ensure_inputs("Q1", args.input_dir)
    os.environ["PYTHONHASHSEED"] = str(args.seed)
    forecast_dir = args.output_dir / "forecast"
    schedule_dir = args.output_dir / "schedule"
    forecast_args = ["--question", "Q1", "--input-dir", str(args.input_dir), "--output-dir", str(forecast_dir), "--seed", str(args.seed)]
    schedule_args = ["--input-dir", str(args.input_dir), "--output-dir", str(schedule_dir), "--seed", str(args.seed)]
    if forecast_core.main(forecast_args) != 0:
        return 2
    return schedule_core.main(schedule_args)


if __name__ == "__main__":
    raise SystemExit(main())
