from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"


class CorpusArtifactTests(unittest.TestCase):
    @staticmethod
    def _source_url(row: dict[str, str]) -> str:
        """Resolve legacy rows whose URL lives only in the raw manifest."""
        source_url = (row.get("source_url") or "").strip()
        if source_url:
            return source_url
        manifest_path = CORPUS / "raw" / row["paper_id"] / "source_manifest.json"
        if not manifest_path.is_file():
            return ""
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = manifest.get("source") or {}
        return str(source.get("url") or source.get("source_url") or "").strip()

    def test_index_cards_and_access_labels(self) -> None:
        with (CORPUS / "index.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 40)
        for row in rows:
            self.assertTrue(self._source_url(row).startswith("https://"), row["paper_id"])
            self.assertTrue(
                row["access"].startswith(("public", "index_only_", "mirror_", "restricted_")),
                row["access"],
            )
            if row["card_file"]:
                self.assertTrue((CORPUS / "cards" / row["card_file"]).is_file())

    def test_index_exposes_evidence_v3_fields(self) -> None:
        with (CORPUS / "index.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = set(reader.fieldnames or [])
        self.assertTrue(
            {
                "card_schema_version",
                "review_status",
                "authenticity_level",
                "pdf_sha256",
                "evidence_page_count",
                "code_link_count",
            }.issubset(fields)
        )
        reviewed = [row for row in rows if row["review_status"] in {"evidence_reviewed", "evidence_deep_read"}]
        self.assertGreaterEqual(len(reviewed), 17)

    def test_manifests_match_cached_files_and_hashes(self) -> None:
        manifests = sorted((CORPUS / "raw").glob("*/source_manifest.json"))
        self.assertGreaterEqual(len(manifests), 6)
        for path in manifests:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            pages = manifest.get("pages") or manifest.get("render", {}).get("pages", [])
            cached_pages = manifest.get("cached_pages") or len(pages)
            self.assertEqual(int(cached_pages), len(pages))
            for page in pages:
                page_path = Path(page["file"])
                if not page_path.is_absolute():
                    root_candidate = CORPUS.parent / page_path
                    page_path = root_candidate if root_candidate.is_file() else path.parent / page_path
                data = page_path.read_bytes()
                self.assertEqual(data[:2], b"\xff\xd8")
                self.assertEqual(len(data), page["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), page["sha256"])

    def test_layout_metrics_reference_manifest_pages(self) -> None:
        with (CORPUS / "layout_metrics.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        observed = {(row["paper_id"], int(row["page"])) for row in rows}
        expected: set[tuple[str, int]] = set()
        for path in (CORPUS / "raw").glob("*/source_manifest.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            pages = manifest.get("pages") or manifest.get("render", {}).get("pages", [])
            expected.update((path.parent.name, int(page["page"])) for page in pages)
        self.assertTrue(observed)
        self.assertTrue(observed.issubset(expected))

    def test_figure_inventory_evidence_exists(self) -> None:
        with (CORPUS / "figure_inventory.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 30)
        for row in rows:
            evidence = CORPUS / "raw" / row["paper_id"] / row["evidence_file"]
            self.assertTrue(evidence.is_file(), evidence)

    def test_top_journal_figure_code_index_is_commit_pinned(self) -> None:
        index_path = CORPUS / "top_journal_figure_code_index.csv"
        with index_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 8)
        for row in rows:
            self.assertTrue(row["journal"].startswith("Nature"), row["journal"])
            self.assertTrue(row["doi"].startswith("10.1038/"), row["doi"])
            self.assertTrue(row["repository"].startswith("https://github.com/"))
            self.assertEqual(len(row["commit"]), 40)
            int(row["commit"], 16)
            self.assertTrue(row["source_paths"])
            self.assertIn(row["evidence_level"], {"A", "A-index-only"})

    def test_historical_cumcm_manifest_counts_completed_visual_reviews(self) -> None:
        manifest = json.loads((CORPUS / "manifests" / "cumcm-deep-read.json").read_text(encoding="utf-8"))
        completed = sum(record.get("visual_review") == "complete" for record in manifest["records"])
        self.assertEqual(manifest["content_reviewed_count"], completed)
        self.assertEqual(completed, manifest["selected"])


if __name__ == "__main__":
    unittest.main()
