#!/usr/bin/env python
"""Run Q3 rolling storage MILP and the corrected 270-item audit."""

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
from code.q3 import full_audit_core, storage_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Q3 storage optimization and audit.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args(argv)
    ensure_inputs("Q3", args.input_dir)
    os.environ["PYTHONHASHSEED"] = str(args.seed)
    common = ["--input-dir", str(args.input_dir), "--output-dir", str(args.output_dir), "--seed", str(args.seed)]
    if storage_core.main(common) != 0:
        return 2
    return full_audit_core.main(common)


if __name__ == "__main__":
    raise SystemExit(main())
