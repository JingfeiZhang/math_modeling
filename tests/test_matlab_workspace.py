from __future__ import annotations

import csv
import hashlib
import json
import struct
import unittest
from pathlib import Path

from src.utils.hash_figure_artifacts import build_manifest

ROOT = Path(__file__).resolve().parents[1]
MATLAB = ROOT / "matlab"
OUTPUT = ROOT / "output" / "_demos" / "matlab" / "matlab_figures"


class MatlabWorkspaceTests(unittest.TestCase):
    def test_matlab_adapter_sources_exist(self) -> None:
        for relative in (
            "scripts/_matlab.ps1",
            "scripts/run_matlab.ps1",
            "matlab/hashFigureArtifacts.m",
            "matlab/recipe_smoke.m",
            "matlab/setup_modeling_path.m",
            "matlab/smoke_test.m",
            "matlab/plotting/applyModelingStyle.m",
            "matlab/plotting/exportModelingFigure.m",
            "matlab/plotting/demo_publication_figure.m",
            "src/utils/hash_figure_artifacts.py",
            "reports/matlab_skill_audit.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

        launcher = (ROOT / "scripts" / "run_matlab.ps1").read_text(encoding="utf-8")
        self.assertNotIn("setx", launcher.lower())
        self.assertIn("$env:MATLAB_ROOT", launcher)
        self.assertNotIn("R2025b", launcher)

        resolver = (ROOT / "scripts" / "_matlab.ps1").read_text(encoding="utf-8")
        self.assertIn("Get-ConfiguredMatlabRoot", resolver)
        self.assertIn("Resolve-MatlabInstallation", resolver)
        self.assertIn("MATLABROOT", resolver)
        self.assertIn("runtime\\win64", resolver)
        self.assertNotIn("R2025b", resolver)

        contest = (ROOT / "contest.yaml").read_text(encoding="utf-8")
        self.assertIn("matlab_root: D:/MATLAB/R2026a", contest)

    def test_matlab_environment_report(self) -> None:
        report = json.loads((ROOT / "output" / "matlab_environment.json").read_text(encoding="utf-8"))
        self.assertEqual(report["matlab"]["release"], "2026a")
        self.assertEqual(Path(report["matlab"]["root"]), Path(r"D:\MATLAB\R2026a"))
        self.assertEqual(report["matlab"]["architecture"], "win64")
        self.assertTrue(report["requiredChecksPassed"])
        for name in ("graphics", "optimization", "globalOptimization", "symbolicMath", "statisticsMachineLearning"):
            self.assertTrue(report["checks"][name], name)
        self.assertTrue(report["optionalStatisticsAvailable"])
        self.assertTrue(report["products"]["statisticsMachineLearning"])
        self.assertTrue(report["capabilities"]["fitlm"])
        self.assertTrue(report["capabilities"]["fitctree"])

        aggregate = json.loads((ROOT / "output" / "environment.json").read_text(encoding="utf-8"))
        self.assertTrue(aggregate["matlab"]["available"])
        self.assertEqual(Path(aggregate["matlab"]["root"]), Path(r"D:\MATLAB\R2026a"))
        self.assertEqual(aggregate["matlab"]["release"], "R2026a")
        self.assertTrue(aggregate["matlab"]["smoke_report"]["matches_installation"])
        self.assertTrue(aggregate["matlab"]["smoke_report"]["statistics_available"])

    def test_publication_figure_artifacts_and_contract(self) -> None:
        expected = {
            "demo.pdf": b"%PDF",
            "demo.png": b"\x89PNG\r\n\x1a\n",
            "demo.svg": b"<?xml",
            "demo_result.csv": None,
            "demo_result.mat": None,
            "demo_figure_contract.json": None,
        }
        for name, signature in expected.items():
            path = OUTPUT / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100, name)
            if signature is not None:
                self.assertTrue(path.read_bytes().startswith(signature), name)

        png = (OUTPUT / "demo.png").read_bytes()
        width, height = struct.unpack(">II", png[16:24])
        self.assertGreaterEqual(width, 2500)
        self.assertGreaterEqual(height, 1100)

        contract = json.loads((OUTPUT / "demo_figure_contract.json").read_text(encoding="utf-8"))
        for field in ("id", "claim", "evidence", "role", "encoding", "axes", "baseline", "caption"):
            self.assertTrue(contract[field], field)
        self.assertEqual(contract["export"], ["pdf", "svg", "png"])

        with (OUTPUT / "demo_result.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 13)
        self.assertIn("ImprovementPct", rows[0])
        self.assertIn("SensitivityMedium", rows[0])

    def test_recipe_visual_hashes_are_reproducible(self) -> None:
        smoke_root = ROOT / "output" / "_demos" / "matlab" / "matlab-recipe-smoke"
        manifests: dict[tuple[str, str], dict] = {}
        for run in ("run1", "run2"):
            for stem in ("sensitivity", "convergence"):
                path = smoke_root / run / f"{stem}.hashes.json"
                self.assertTrue(path.is_file(), path)
                payload = json.loads(path.read_text(encoding="utf-8"))
                manifests[(run, stem)] = payload
                self.assertIn("provenance", payload["artifacts"]["pdf"]["determinism_role"])
                self.assertIn("metadata may change raw bytes", payload["reproducibility_note"])
                for suffix in ("pdf", "svg", "png"):
                    artifact = smoke_root / run / f"{stem}.{suffix}"
                    self.assertEqual(
                        payload["artifacts"][suffix]["raw_sha256"],
                        hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    )
                independent = build_manifest(smoke_root / run, stem)
                self.assertEqual(
                    payload["artifacts"]["svg"]["canonical_sha256"],
                    independent["artifacts"]["svg"]["canonical_sha256"],
                )
                self.assertEqual(
                    payload["artifacts"]["png"]["pixel_sha256"],
                    independent["artifacts"]["png"]["pixel_sha256"],
                )

        for stem in ("sensitivity", "convergence"):
            first = manifests[("run1", stem)]["artifacts"]
            second = manifests[("run2", stem)]["artifacts"]
            self.assertEqual(first["svg"]["canonical_sha256"], second["svg"]["canonical_sha256"])
            self.assertEqual(first["png"]["pixel_sha256"], second["png"]["pixel_sha256"])


if __name__ == "__main__":
    unittest.main()
