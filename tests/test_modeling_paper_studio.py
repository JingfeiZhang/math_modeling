from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill_staging" / "modeling-paper-studio"


class ModelingPaperStudioTests(unittest.TestCase):
    def test_skill_metadata_and_resources(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: modeling-paper-studio", skill_text)
        self.assertNotIn("[TODO", skill_text)
        openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$modeling-paper-studio", openai_yaml)
        for relative in (
            "scripts/audit_latex.py",
            "scripts/audit_figures.py",
            "references/latex-layout.md",
            "references/contest-writing.md",
            "references/scientific-figures.md",
            "references/figure-brief.md",
            "references/physical-size-and-type.md",
            "references/modeling-figure-archetypes.md",
            "references/statistics-and-integrity.md",
            "references/visual-hierarchy.md",
            "references/rendered-figure-qa.md",
            "references/template-families.md",
            "references/matlab-figure-recipes.md",
            "references/corpus-mining-handoff.md",
            "references/multi-agent-handoff.md",
            "references/top-journal-figure-code.md",
            "references/upstream-skill-patterns.md",
            "references/empirical-exemplars.md",
            "references/audit-contract.md",
            "assets/latex-template/main.tex",
        ):
            self.assertTrue((SKILL / relative).is_file(), relative)

        upstream = (SKILL / "references" / "upstream-skill-patterns.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("11f38624cd9128bc2ce22d7b3254106e624490cd", upstream)
        self.assertIn("50a2942007a98e74cd0948b44d7cb8e4826d15c9", upstream)
        self.assertIn("1df9940dd01ac939f072b12fe28d6353b79b90f9", upstream)
        self.assertIn("mathmodel-skill", upstream)
        self.assertIn("可运行基线", upstream)
        self.assertIn("冻结", upstream)

    def test_auditors_accept_good_fixture_and_reject_bad_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            good = root / "good"
            (good / "figures").mkdir(parents=True)
            (good / "figures" / "result.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240"/>',
                encoding="utf-8",
            )
            (good / "main.tex").write_text(
                r"""\documentclass{article}
\usepackage{graphicx}
\begin{document}
\begin{abstract}审计测试摘要。\end{abstract}
\section{结果}见图~\ref{fig:result}。
\begin{figure}
\includegraphics{figures/result.svg}
\caption{优化方案与基线收益（万元）。}
\label{fig:result}
\end{figure}
\end{document}
""",
                encoding="utf-8",
            )
            evidence_path = good / "results" / "q1.json"
            evidence_path.parent.mkdir()
            evidence_path.write_text('{"profit": 12.0}', encoding="utf-8")
            import hashlib
            manifest = {
                "schema_version": "2.0",
                "figures": [{
                    "contract_version": "2.0",
                    "id": "fig-result",
                    "question_id": "Q1",
                    "claim_id": "q1-result",
                    "kind": "data",
                    "backend": "python",
                    "source_script": "good/plot.py",
                    "outputs": {
                        "pdf": "good/figures/result.pdf",
                        "svg": "good/figures/result.svg",
                        "png": "good/figures/result.png",
                        "png_dpi": 400,
                    },
                    "core_conclusion": "优化方案相对原方案提高收益",
                    "evidence_chain": [{
                        "locator": "good/results/q1.json:profit",
                        "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                        "fields": ["profit"],
                    }],
                    "archetype": "paired-comparison",
                    "axes": [
                        {"variable": "时间", "unit": "h"},
                        {"variable": "收益", "unit": "万元"},
                    ],
                    "baseline": "原方案",
                    "panel_map": [{"panel": "main", "role": "comparison", "subclaim": "优化方案与基线对比"}],
                    "caption": "优化方案与基线收益（万元）。",
                    "review_risks": ["样本量较小"],
                    "final_width_mm": 145,
                    "min_font_pt": 8,
                    "source_data": ["good/results/q1.json"],
                    "statistics": ["paired comparison"],
                }],
            }
            (good / "plot.py").write_text("# plotting fixture\n", encoding="utf-8")
            (good / "figures" / "result.pdf").write_bytes(b"%PDF-1.4 fixture")
            (good / "figures" / "result.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            (good / "figure_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )

            latex = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "audit_latex.py"), "--paper-dir", str(good)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            figures = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "audit_figures.py"), "--paper-dir", str(good)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(latex.returncode, 0, latex.stdout + latex.stderr)
            self.assertEqual(figures.returncode, 0, figures.stdout + figures.stderr)

            bad = root / "bad"
            (bad / "figures").mkdir(parents=True)
            (bad / "figures" / "screenshot.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8"
            )
            (bad / "main.tex").write_text(
                r"""\documentclass{article}
\usepackage{graphicx}
\begin{document}
\begin{abstract}摘要。\end{abstract}
\section{结果}见图~\ref{fig:missing}。
\begin{figure}\includegraphics{figures/screenshot.svg}\caption{结果。}\end{figure}
\end{document}
""",
                encoding="utf-8",
            )
            (bad / "figure_manifest.json").write_text("[]", encoding="utf-8")
            latex_bad = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "audit_latex.py"), "--paper-dir", str(bad)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            figures_bad = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "audit_figures.py"), "--paper-dir", str(bad)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertNotEqual(latex_bad.returncode, 0)
            self.assertIn("UNDEFINED_REF", latex_bad.stdout)
            self.assertNotEqual(figures_bad.returncode, 0)
            self.assertIn("SCREENSHOT_FILE", figures_bad.stdout)


if __name__ == "__main__":
    unittest.main()
