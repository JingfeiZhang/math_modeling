from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from src.utils import audit_latex


ARGUMENT_HEADINGS = (
    "目标与上下游接口",
    "数据特征或机理依据",
    "模型选择与备选方案比较",
    "模型建立",
    "求解算法",
    "核心结果与解释",
    "模型检验",
    "本问结论与适用边界",
)

VALID_ABSTRACT = (
    "针对问题一，采用Q1正式模型得到q1-result，并以q1-validation完成误差与稳健性检验；"
    "针对问题二，采用Q2正式模型得到q2-result，并以q2-validation完成约束与稳定性检验。"
    "两个问题的结论均限定在题目给定条件内。"
)


def _question_tex(number: str, claim_prefix: str, artifact: str) -> str:
    parts = [f"\\section{{问题{number}：模型建立与求解}}"]
    for heading in ARGUMENT_HEADINGS:
        parts.append(f"\\subsection{{{heading}}}")
        parts.append("本节围绕题目给定变量建立可计算关系，说明输入、输出、约束、求解步骤以及结果成立的条件。")
    parts.append(f"正式结果引用 {claim_prefix}-result、{claim_prefix}-validation 和 {claim_prefix}-boundary。")
    if artifact.startswith("fig:"):
        parts.extend(
            [
                f"由图\\ref{{{artifact}}}可见，模型结果与基线之间存在稳定差异，该差异回答了本问的核心决策。",
                "\\begin{figure}",
                "\\includegraphics{dummy.png}",
                "\\caption{模型结果与基线比较}",
                f"\\label{{{artifact}}}",
                "\\end{figure}",
                "图中变化来自约束和输入条件的共同作用，结果表明所给方案在规定范围内可行。",
            ]
        )
    else:
        parts.extend(
            [
                f"表\\ref{{{artifact}}}汇总核心指标，数值与基线保持相同输出口径。",
                "\\begin{table}",
                "\\caption{核心结果比较}",
                f"\\label{{{artifact}}}",
                "\\begin{tabular}{cc}指标&结果\\\\\\hline A&1\\end{tabular}",
                "\\end{table}",
                "表中结果说明模型满足约束，且检验结论支持本问给出的最终答案。",
            ]
        )
    return "\n".join(parts)


def _manifest(question_id: str, section: str, artifact_field: str, artifact: str, prefix: str) -> dict:
    return {
        "schema_version": 2,
        "problem_id": "C",
        "question_id": question_id,
        "model_selection": {"primary": f"{question_id}正式模型", "rationale": "适配约束", "baseline": "同输出基线"},
        "evidence": {
            "result_claim_ids": [f"{prefix}-result"],
            "validation_claim_ids": [f"{prefix}-validation"],
            "boundary_claim_ids": [f"{prefix}-boundary"],
        },
        "paper": {
            "section": section,
            "figure_ids": [artifact] if artifact_field == "figure_ids" else [],
            "table_ids": [artifact] if artifact_field == "table_ids" else [],
            "code_refs": [f"code/{question_id.lower()}.py"],
            "downstream_interfaces": ["下一问输入" if question_id == "Q1" else "最终输出"],
            "argument_contract": {key: "completed" for key in audit_latex.QUESTION_ARGUMENT_KEYS},
        },
    }


def _args(paper: Path, log: Path) -> argparse.Namespace:
    return argparse.Namespace(
        paper_dir=str(paper),
        contest_config=None,
        pdf=None,
        log=str(log),
        output=None,
        max_pages=30,
        max_pdf_mb=20.0,
        min_margin_cm=2.5,
        abstract_char_warning=1500,
        require_anonymous=False,
        structure_strict=True,
    )


def _write_valid_project(tmp_path: Path, abstract: str) -> tuple[Path, Path]:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "dummy.png").write_bytes(b"fixture")
    main = "\n".join(
        [
            "\\documentclass{article}",
            "\\usepackage[margin=2.5cm]{geometry}",
            "\\begin{document}",
            f"\\begin{{abstract}}{abstract}\\end{{abstract}}",
            "\\section{问题重述}",
            "本文概括题目给定条件、需要完成的任务以及两个子问题之间的输入输出关系。",
            "\\section{问题分析}",
            "两个问题分别属于预测与约束优化，需要在统一指标口径下完成结果传递。",
            "\\section{模型假设与符号约定}",
            "假设仅覆盖后续模型实际使用的边界条件，核心符号在本节统一定义。",
            "\\section{数据处理与评价指标}",
            "数据按统一粒度处理，并采用可比较的误差和可行性指标评价模型。",
            _question_tex("一", "q1", "fig:q1"),
            _question_tex("二", "q2", "tab:q2"),
            "\\section{模型评价与推广}",
            "模型的优点、局限和适用范围均由前述检验结果支持。",
            "已有研究给出了相关建模基础\\UpCite{ref-a}，进一步方法见文献\\UpCite{ref-b}。",
            "\\section*{参考文献}",
            "\\begin{thebibliography}{9}",
            "\\bibitem{ref-a} 作者甲. 文献甲.",
            "\\bibitem{ref-b} Author B. Reference B.",
            "\\end{thebibliography}",
            "\\appendix",
            "\\section{附录：关键程序}",
            "附录给出关键程序入口和复现命令。",
            "\\end{document}",
        ]
    )
    (paper / "main.tex").write_text(main, encoding="utf-8")
    log = paper / "main.log"
    log.write_text("Output written on main.pdf (4 pages).\n", encoding="utf-8")
    for qid, field, artifact, prefix in (
        ("Q1", "figure_ids", "fig:q1", "q1"),
        ("Q2", "table_ids", "tab:q2", "q2"),
    ):
        folder = tmp_path / "problems" / "C" / "questions" / qid
        folder.mkdir(parents=True)
        manifest = _manifest(qid, f"sections/question_{qid[-1]}.tex", field, artifact, prefix)
        (folder / "question.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return paper, log


def test_v3_structure_and_evidence_contract_passes(tmp_path: Path) -> None:
    paper, log = _write_valid_project(tmp_path, VALID_ABSTRACT)

    result = audit_latex.audit(_args(paper, log))

    assert result["passed"] is True, result["errors"]
    assert result["metrics"]["question_sections"] == [1, 2]
    assert result["metrics"]["question_manifests"] == 2


def test_v3_abstract_requires_per_question_method_result_and_validation(tmp_path: Path) -> None:
    abstract_without_q2 = (
        "针对问题一，采用Q1正式模型得到q1-result，并以q1-validation完成误差与稳健性检验。"
        "全文还讨论了另一项任务，但摘要没有给出该任务的方法、量化结果和验证结论。"
    )
    paper, log = _write_valid_project(tmp_path, abstract_without_q2)

    result = audit_latex.audit(_args(paper, log))
    coverage_errors = [item for item in result["errors"] if item["code"] == "ABSTRACT_QUESTION_COVERAGE"]

    assert result["passed"] is False
    assert coverage_errors
    assert "Q2" in coverage_errors[0]["message"]


def test_v3_structure_reports_contract_and_log_failures(tmp_path: Path) -> None:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        """\\documentclass{article}
\\usepackage[margin=2.5cm]{geometry}
\\begin{document}
\\tableofcontents
\\begin{abstract}这是一个足够长的摘要，但没有改变本测试对结构错误、证据缺口和编译日志错误的检查目标。\\end{abstract}
\\section{问题分析}内容。
\\section{问题重述}内容。
\\section{模型假设与符号约定}内容。
\\section{数据处理与评价指标}内容。
\\section{问题一：模型建立与求解}
\\WritingContract{目标}{内容}{证据}{禁区}
\\subsection{模型建立}q1-result。
文献\\UpCite{ref-b}后引用\\UpCite{ref-a}。
图\\ref{dup}说明结果。
\\begin{figure}\\caption{重复标签}\\label{dup}\\end{figure}
\\label{dup}
\\begin{table}\\caption{未引用表}\\label{tab:orphan}\\end{table}
\\section{问题二：模型建立与求解}内容。
\\section{模型评价与推广}内容。
\\section*{参考文献}
\\begin{thebibliography}{9}\\bibitem{ref-a}A.\\bibitem{ref-b}B.\\end{thebibliography}
\\appendix
\\section{附录}
\\subsection{符号表}重复符号。
\\end{document}
""",
        encoding="utf-8",
    )
    log = paper / "main.log"
    log.write_text(
        "Overfull \\hbox (10.0pt too wide)\n"
        "LaTeX Warning: Reference `missing' on page 1 undefined.\n"
        "LaTeX Warning: Citation `missing-ref' on page 1 undefined.\n"
        "LaTeX Warning: Label `dup' multiply defined.\n",
        encoding="utf-8",
    )
    folder = tmp_path / "problems" / "C" / "questions" / "Q1"
    folder.mkdir(parents=True)
    manifest = _manifest("Q1", "sections/question_1.tex", "figure_ids", "fig:q1", "q1")
    manifest["paper"]["argument_contract"]["validation"] = "pending"
    manifest["evidence"]["validation_claim_ids"] = []
    (folder / "question.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")

    result = audit_latex.audit(_args(paper, log))
    codes = {item["code"] for item in result["errors"]}

    assert {
        "TOC_FORBIDDEN",
        "SECTION_ORDER",
        "QUESTION_COUNT_MISMATCH",
        "APPENDIX_SYMBOL_TABLE",
        "AUTHORING_PROMPT",
        "ARGUMENT_CONTRACT_INCOMPLETE",
        "QUESTION_EVIDENCE_MISSING",
        "DUPLICATE_LABEL",
        "ARTIFACT_UNREFERENCED",
        "BIB_ORDER",
        "OVERFULL_BOX",
        "LOG_UNDEFINED_REFERENCE",
        "LOG_UNDEFINED_CITATION",
        "LOG_DUPLICATE_LABEL",
    } <= codes
