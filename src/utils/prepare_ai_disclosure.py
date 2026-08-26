#!/usr/bin/env python3
"""Prepare concise CUMCM AI disclosure artifacts from internal evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

try:
    from . import aggregate_ai_usage  # type: ignore
except ImportError:  # direct script execution
    import aggregate_ai_usage  # type: ignore


STAGE_PARAGRAPHS = {
    "problem_analysis": (
        "问题分析与思路拓展",
        "AI工具用于辅助梳理题目条件、变量关系、约束和候选建模思路，并提供方法适用性的参考。"
        "参赛队员结合题目要求、数据特征及可验证性进行比较，确认最终问题定义和建模方向。",
    ),
    "modeling_implementation": (
        "模型与算法实现辅助",
        "AI工具用于辅助解释部分模型与算法原理、检查数学表达，并提供程序实现和调试建议。"
        "模型假设、变量定义、目标函数、约束条件、参数设置及正式程序由参赛队员结合实际问题进行确定、修改和运行。",
    ),
    "experiment_validation": (
        "实验检查与结果分析",
        "AI工具用于辅助定位程序问题、提出验证与敏感性分析思路，并帮助解释部分实验现象。"
        "正式实验、指标计算、约束检查和结果取舍均由参赛队员依据实际运行结果完成并核验。",
    ),
    "paper_writing": (
        "论文表达辅助",
        "AI工具用于辅助整理文字结构、改善表达和检查局部表述。"
        "论文中的模型逻辑、数据、图表、实验结果和最终结论均由参赛队员依据冻结证据审核并定稿。",
    ),
}


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def dump_yaml(path: Path, value: dict) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def compact_list(values: list[str], limit: int = 3) -> str:
    cleaned = [value.strip().replace("\n", " ") for value in values if value and value.strip()]
    return "；".join(cleaned[:limit])


def used_stage_titles(summary: dict) -> list[str]:
    return [STAGE_PARAGRAPHS[key][0] for key, value in summary.get("stages", {}).items() if value.get("used")]


def make_statement(policy: dict, mode: str, summary: dict) -> str:
    disclosure = policy.get("disclosure", {})
    if mode == "not_used":
        return str(disclosure.get("no_ai_text") or "本参赛队在竞赛过程中未使用任何AI工具。") + "\n"
    titles = used_stage_titles(summary)
    scope = "、".join(titles) if titles else "问题分析、模型与算法实现、实验检查和论文表达"
    return (
        f"本参赛队在竞赛过程中使用了AI工具，主要用于{scope}等辅助工作。"
        "相关建议和生成内容均由参赛队员结合题目条件、实际程序运行和实验结果进行人工审核与验证，详细使用情况见支撑材料。\n"
    )


def make_details_tex(summary: dict) -> str:
    tools = summary.get("tools", [])
    tool_text = "；".join(
        f"{item.get('tool', '').strip()}（{item.get('model_version', '').strip()}）" for item in tools
        if item.get("tool") and item.get("model_version")
    ) or "按内部使用记录列示的生成式人工智能工具"

    sections: list[str] = []
    for key in ("problem_analysis", "modeling_implementation", "experiment_validation", "paper_writing"):
        data = summary.get("stages", {}).get(key, {})
        if not data.get("used"):
            continue
        title, base = STAGE_PARAGRAPHS[key]
        purpose_text = compact_list(list(data.get("purposes", [])))
        theme_text = compact_list(list(data.get("prompt_themes", [])), limit=2)
        extra = ""
        if purpose_text:
            extra += f" 主要用途包括：{purpose_text}。"
        if theme_text:
            extra += f" 提示内容主要围绕：{theme_text}。"
        sections.append(
            "\\subsection*{" + latex_escape(title) + "}\n" + latex_escape(base + extra) + "\n"
        )

    body = "\n".join(sections)
    return r"""\documentclass[11pt,a4paper]{ctexart}
\usepackage[margin=2.5cm]{geometry}
\usepackage{enumitem}
\setlength{\parindent}{2em}
\setlength{\parskip}{0.35em}
\pagestyle{plain}
\begin{document}
\begin{center}
{\Large\bfseries AI工具使用详情}
\end{center}

\subsection*{使用工具及模型}
""" + latex_escape(tool_text) + "\n\n" + body + r"""
\subsection*{人工审核与验证}
对于AI工具产生的候选建模思路、数学表达、程序建议、实验解释和文字内容，参赛队员均结合题目条件、理论依据、baseline、正式程序运行结果及相应验证证据进行人工检查、修改或取舍。AI输出本身不作为正式实验结果或论文数值证据；论文中的正式数据、图表、指标和结论均以本队实际运行并冻结的证据为准。

\end{document}
"""


def compile_details(tex_path: Path, pdf_path: Path) -> None:
    xelatex = shutil.which("xelatex")
    if not xelatex:
        raise RuntimeError("xelatex is required to build AI工具使用详情.pdf")
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    command = [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    for _ in range(2):
        run = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if run.returncode != 0:
            tail = (run.stdout + "\n" + run.stderr)[-4000:]
            raise RuntimeError(f"AI details XeLaTeX failed:\n{tail}")
    built = tex_path.with_suffix(".pdf")
    if not built.is_file():
        raise RuntimeError("XeLaTeX completed without producing AI details PDF")
    if built.resolve() != pdf_path.resolve():
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, pdf_path)


def prepare(root: Path, policy_path: Path, compile_pdf: bool) -> dict:
    policy = load_yaml(policy_path)
    contest = load_yaml(root / "contest.yaml")
    formal = str(contest.get("problem", "TBD")).strip().upper() != "TBD"
    state_cfg = policy.get("state", {})
    state_path = (root / state_cfg.get("path", "output/ai_usage_state.yaml")).resolve()
    state = load_yaml(state_path) if state_path.is_file() else {}
    mode = str(state.get("mode") or "").strip().lower()

    if not formal:
        return {"status": "PRECONTEST_NOOP", "formal": False, "mode": mode or None}
    if mode not in {"used", "not_used"}:
        raise RuntimeError(f"formal project requires explicit AI mode in {state_path}")

    summary = aggregate_ai_usage.aggregate(root, policy_path, mode)
    summary_path = (root / policy.get("aggregation", {}).get("output", "output/ai/stage_summary.yaml")).resolve()
    dump_yaml(summary_path, summary)

    if mode == "used" and not summary.get("tools"):
        raise RuntimeError("AI mode is used but no tool/model entries were found in the internal AI log")
    if mode == "used" and summary.get("unclassified_events"):
        raise RuntimeError(f"AI usage contains unclassified events: {summary['unclassified_events']}")

    disclosure = policy.get("disclosure", {})
    statement_path = (root / disclosure.get("generated_statement_locator", "paper/generated/ai_usage_statement.tex")).resolve()
    statement_path.parent.mkdir(parents=True, exist_ok=True)
    statement_path.write_text(make_statement(policy, mode, summary), encoding="utf-8")

    details_cfg = policy.get("details", {})
    tex_path = (root / details_cfg.get("generated_tex", "output/ai/generated/AI工具使用详情.tex")).resolve()
    pdf_path = (root / details_cfg.get("generated_pdf", "output/ai/generated/AI工具使用详情.pdf")).resolve()
    package_source = (root / details_cfg.get("package_source", "src/submission/manifest/AI工具使用详情.pdf")).resolve()

    if mode == "not_used":
        for stale in (tex_path, pdf_path, package_source):
            if stale.is_file():
                stale.unlink()
        return {
            "status": "READY",
            "formal": True,
            "mode": mode,
            "statement": str(statement_path),
            "summary": str(summary_path),
            "details_pdf": None,
        }

    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(make_details_tex(summary), encoding="utf-8")
    if compile_pdf:
        compile_details(tex_path, pdf_path)
        package_source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, package_source)

    return {
        "status": "READY" if (not compile_pdf or pdf_path.is_file()) else "INCOMPLETE",
        "formal": True,
        "mode": mode,
        "statement": str(statement_path),
        "summary": str(summary_path),
        "details_tex": str(tex_path),
        "details_pdf": str(pdf_path) if pdf_path.is_file() else None,
        "package_source": str(package_source) if package_source.is_file() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--compile-details", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = prepare(args.root.resolve(), args.policy.resolve(), args.compile_details)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
