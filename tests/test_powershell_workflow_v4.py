from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell") or shutil.which("powershell.exe")
BUILD_SCRIPT = ROOT / "scripts" / "build_paper.ps1"
WORKFLOW_SCRIPT = ROOT / "scripts" / "workflow.ps1"
RUN_SCRIPT = ROOT / "scripts" / "run_experiment.ps1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(POWERSHELL, "Windows PowerShell is unavailable")
class PowerShellWorkflowV4Tests(unittest.TestCase):
    def test_entrypoints_parse_with_powershell_ast(self) -> None:
        for path in (BUILD_SCRIPT, WORKFLOW_SCRIPT, RUN_SCRIPT):
            command = (
                "$tokens=$null; $errors=$null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tokens,[ref]$errors) | Out-Null; "
                "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v4_routes_and_legacy_routes_are_declared(self) -> None:
        text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")
        for action in (
            "quickcheck",
            "checkpoint",
            "promote",
            "paper-evidence",
            "layout-check",
            "archive-work",
            "prepare-sprint",
            "preview",
            "build",
            "audit",
            "package",
            "figure-data",
            "figure-intent",
            "figure-brief",
            "figure-render",
            "figure-qa",
            "figure-promote",
        ):
            self.assertIn(f"'{action}'", text)
        self.assertIn("[string]$RunId", text)
        self.assertIn("[string]$Intent", text)
        self.assertIn("[string]$Brief", text)
        self.assertIn("[string]$Outputs", text)
        self.assertIn("[string]$Qa", text)
        self.assertIn("[string]$FigureId", text)
        self.assertIn("promote requires -Question and -RunId", text)
        self.assertIn("paper-evidence requires -Question and -Config", text)
        self.assertIn("figure-data requires -Question, -RunId, and -Config", text)
        self.assertIn("figure-intent requires -Question, -RunId, and -Config", text)
        self.assertIn("figure-brief requires -Question, -RunId, -Intent, and -Config", text)
        self.assertIn("figure-render requires -Question, -RunId, and -Brief", text)
        self.assertIn("figure-qa requires -Question, -RunId, -Brief, and -Outputs", text)
        self.assertIn("figure-promote requires -Question, -FigureId, -Brief, and -Qa", text)
        self.assertIn("-PreviewCheckpoint $PreviewCheckpoint", text)

    def test_powershell_routes_match_python_cli_contract(self) -> None:
        cli = ROOT / "src" / "workflow" / "competition_workflow.py"
        expected = {
            "quickcheck": ("--problem", "--question", "--strict"),
            "checkpoint": ("--problem", "--question", "--strict"),
            "promote": ("--problem", "--question", "--run-id"),
            "paper-evidence": ("--problem", "--question", "--config", "--strict"),
            "archive-work": ("--problem", "--question"),
            "figure-data": ("--problem", "--question", "--run-id", "--config"),
            "figure-intent": ("--problem", "--question", "--run-id", "--config"),
            "figure-brief": ("--problem", "--question", "--run-id", "--intent", "--config"),
            "figure-render": ("--problem", "--question", "--run-id", "--brief"),
            "figure-qa": ("--problem", "--question", "--run-id", "--brief", "--outputs"),
            "figure-promote": ("--problem", "--question", "--figure-id", "--brief", "--qa"),
        }
        for action, flags in expected.items():
            with self.subTest(action=action):
                result = subprocess.run(
                    [sys.executable, str(cli), action, "--help"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                for flag in flags:
                    self.assertIn(flag, result.stdout)

    def test_low_cost_routes_do_not_invoke_pdf_or_package_scripts(self) -> None:
        text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")
        for action in ("quickcheck", "checkpoint", "figure-data", "figure-intent", "figure-brief"):
            start = text.index(f"    '{action}' {{")
            end = text.index("\n    }", start)
            block = text[start:end]
            self.assertIn("Invoke-WorkflowPython", block)
            self.assertNotIn("build_paper.ps1", block)
            self.assertNotIn("audit_submission.ps1", block)
            self.assertNotIn("package_submission.ps1", block)

    def test_build_precedes_g5_and_layout_routes_do_not_validate_g5(self) -> None:
        text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")

        def action_block(action: str, next_action: str) -> str:
            start = text.index(f"    '{action}' {{")
            end = text.index(f"    '{next_action}' {{", start)
            return text[start:end]

        build = action_block("build", "audit")
        self.assertIn("build_paper.ps1", build)
        self.assertNotIn("New-ValidationArguments", build)
        self.assertNotIn("G5", build)

        preview = action_block("preview", "build")
        layout = action_block("layout-check", "archive-work")
        for block in (preview, layout):
            self.assertIn("Invoke-LayoutPreview", block)
            self.assertNotIn("G5", block)

        audit = action_block("audit", "package")
        package = action_block("package", "seal")
        self.assertIn("GateName 'G5'", audit)
        self.assertIn("GateName 'G5'", package)

    def test_paper_evidence_diagnostic_arguments_reach_python_runner(self) -> None:
        text = RUN_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$runConfig.run_mode -eq 'paper-evidence'", text)
        self.assertIn("$runConfig.diagnostic_arguments", text)

    def test_paper_evidence_runs_before_backend_review(self) -> None:
        text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")
        start = text.index("    'paper-evidence' {")
        end = text.index("    'layout-check' {", start)
        block = text[start:end]
        run_position = block.index("run_experiment.ps1")
        review_position = block.index("Invoke-WorkflowPython")
        self.assertLess(run_position, review_position)
        self.assertIn("config must remain inside the selected project root", block)
        self.assertNotIn("G5", block)

    def test_incremental_preview_is_scoped_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / "project"
            paper = project / "paper"
            sections = paper / "sections"
            generated = paper / "generated"
            tools = base / "tools"
            for folder in (sections, generated, tools):
                folder.mkdir(parents=True, exist_ok=True)

            (paper / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "front\n"
                "\\input{sections/data_processing.tex}\n"
                "\\IfFileExists{generated/question_structure.tex}{\\input{generated/question_structure.tex}}{}\n"
                "tail\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            (sections / "data_processing.tex").write_text("data\n", encoding="utf-8")
            for number in range(1, 4):
                (sections / f"question_{number}.tex").write_text(f"question {number}\n", encoding="utf-8")
            structure = generated / "question_structure.tex"
            structure.write_text(
                "\\input{sections/question_1.tex}\n"
                "\\input{sections/question_2.tex}\n"
                "\\input{sections/question_3.tex}\n",
                encoding="utf-8",
            )

            (tools / "latexmk.ps1").write_text(
                "$structure = Get-Content -LiteralPath 'generated/question_structure.tex' -Raw -Encoding UTF8\n"
                "Set-Content -LiteralPath $env:MATHMODEL_PREVIEW_CAPTURE -Value $structure -Encoding UTF8\n"
                "Set-Content -LiteralPath $env:MATHMODEL_PREVIEW_WORKDIR -Value (Get-Location).Path -Encoding UTF8\n"
                "[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'main.pdf'), \"%PDF-1.4`n%%EOF`n\", [System.Text.Encoding]::ASCII)\n"
                "exit 0\n",
                encoding="utf-8",
            )
            (tools / "pdftoppm.ps1").write_text(
                "$prefix = $args[$args.Count - 1]\n"
                "Set-Content -LiteralPath ($prefix + '-1.png') -Value 'png' -Encoding ASCII\n"
                "exit 0\n",
                encoding="utf-8",
            )

            original_hashes = {path.relative_to(paper): sha256(path) for path in paper.rglob("*") if path.is_file()}
            expected = {
                "frontmatter": ((), True),
                "Q2": ((1, 2), True),
                "full": ((1, 2, 3), False),
            }
            for checkpoint, (question_numbers, early_end) in expected.items():
                with self.subTest(checkpoint=checkpoint):
                    capture = base / f"{checkpoint}-structure.txt"
                    workdir_capture = base / f"{checkpoint}-workdir.txt"
                    output_pdf = project / "output" / f"{checkpoint}.pdf"
                    render_dir = project / "output" / f"{checkpoint}-pages"
                    environment = os.environ.copy()
                    environment["PATH"] = str(tools) + os.pathsep + environment.get("PATH", "")
                    environment["MATHMODEL_PREVIEW_CAPTURE"] = str(capture)
                    environment["MATHMODEL_PREVIEW_WORKDIR"] = str(workdir_capture)
                    result = subprocess.run(
                        [
                            POWERSHELL,
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(BUILD_SCRIPT),
                            "-ProjectRoot",
                            str(project),
                            "-WorkspaceRoot",
                            str(ROOT),
                            "-PreviewCheckpoint",
                            checkpoint,
                            "-OutputPdf",
                            str(output_pdf),
                            "-RenderDir",
                            str(render_dir),
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=environment,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    compiled_structure = capture.read_text(encoding="utf-8-sig")
                    for number in range(1, 4):
                        marker = f"sections/question_{number}.tex"
                        self.assertEqual(marker in compiled_structure, number in question_numbers)
                    self.assertEqual("\\end{document}" in compiled_structure, early_end)
                    self.assertTrue(output_pdf.read_bytes().startswith(b"%PDF"))
                    self.assertTrue((render_dir / "page-1.png").is_file())
                    temporary_workdir = Path(workdir_capture.read_text(encoding="utf-8-sig").strip())
                    self.assertFalse(temporary_workdir.exists())

            current_hashes = {path.relative_to(paper): sha256(path) for path in paper.rglob("*") if path.is_file()}
            self.assertEqual(current_hashes, original_hashes)
            self.assertFalse((paper / "main.pdf").exists())
            self.assertFalse((paper / "main.aux").exists())


if __name__ == "__main__":
    unittest.main()
