"""Audit the deterministic Python single-figure publication demo suite."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.audit_pdf_visual import audit as audit_pdf  # noqa: E402
from src.utils.figure_style import publication_profile, validate_grayscale  # noqa: E402


MIN_PNG_WIDTH = 2200
MIN_PNG_HEIGHT = 1250
REQUIRED_CONTRACT_FIELDS = {
    "synthetic_fixture",
    "contest_evidence_eligible",
    "backend",
    "palette_id",
    "core_conclusion",
    "evidence_chain",
    "source_data",
    "source_script",
    "outputs",
    "baseline",
    "axes",
    "statistics",
    "review_risks",
    "color_encoding",
    "final_width_mm",
    "min_font_pt",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contact_sheet(images: list[tuple[str, Image.Image]], output: Path, *, grayscale: bool) -> None:
    tile_width, tile_height = 760, 520
    columns = 2
    rows = (len(images) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")
    for index, (label, source) in enumerate(images):
        image = source.convert("L").convert("RGB") if grayscale else source.convert("RGB")
        image.thumbnail((tile_width - 34, tile_height - 52), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_width, tile_height), "white")
        tile.paste(image, ((tile_width - image.width) // 2, 24 + (tile_height - 48 - image.height) // 2))
        draw = ImageDraw.Draw(tile)
        draw.text((12, 7), label, fill="#1F2933")
        draw.rectangle((0, 0, tile_width - 1, tile_height - 1), outline="#D9DEE5", width=2)
        canvas.paste(tile, ((index % columns) * tile_width, (index // columns) * tile_height))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, dpi=(150, 150))


def _svg_text_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return sum(1 for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text")


def _hash_map(path: Path) -> dict[str, str]:
    payload = _load_json(path)
    return {item["path"]: item["sha256"] for item in payload["files"]}


def _raster_salience(image: Image.Image) -> dict[str, float]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    saturation = np.divide(maximum - minimum, maximum, out=np.zeros_like(maximum), where=maximum > 0)
    nonwhite = np.any(rgb < 0.965, axis=2)
    colored = nonwhite & (saturation > 0.16)
    high_saturation = nonwhite & (saturation > 0.48)
    dark = maximum < (45 / 255)
    return {
        "nonwhite_pixel_fraction": round(float(nonwhite.mean()), 6),
        "colored_pixel_fraction": round(float(colored.mean()), 6),
        "high_saturation_fraction": round(float(high_saturation.mean()), 6),
        "dark_pixel_fraction": round(float(dark.mean()), 6),
    }


def _compare_runs(primary: Path, reference: Path, figures: list[dict]) -> dict:
    rows = []
    errors = []
    for figure in figures:
        demo_id = figure["id"]
        left = primary / demo_id
        right = reference / demo_id
        row = {"id": demo_id}
        try:
            left_artifacts = _load_json(left / "artifact_hashes.json")["artifacts"]
            right_artifacts = _load_json(right / "artifact_hashes.json")["artifacts"]
            row["data_equal"] = _hash_map(left / "data_hashes.json") == _hash_map(right / "data_hashes.json")
            row["svg_canonical_equal"] = left_artifacts["svg"]["canonical_sha256"] == right_artifacts["svg"]["canonical_sha256"]
            row["png_pixel_equal"] = left_artifacts["png"]["pixel_sha256"] == right_artifacts["png"]["pixel_sha256"]
            row["passed"] = row["data_equal"] and row["svg_canonical_equal"] and row["png_pixel_equal"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
            row.update({"passed": False, "error": str(exc)})
        if not row["passed"]:
            errors.append({"code": "NONDETERMINISTIC_FIGURE", "figure": demo_id, "details": row})
        rows.append(row)
    return {"schema_version": 1, "passed": not errors, "figures": rows, "errors": errors}


def audit_suite(root: Path, dpi: int, reference_root: Path | None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    rows: list[dict] = []
    images: list[tuple[str, Image.Image]] = []
    salience_limits = publication_profile()["raster_salience"]
    manifest_path = root / "suite_manifest.json"
    if not manifest_path.is_file():
        return {"schema_version": 1, "passed": False, "errors": [{"code": "SUITE_MANIFEST_MISSING", "path": str(manifest_path)}], "warnings": [], "figures": []}
    manifest = _load_json(manifest_path)
    figures = manifest.get("figures", [])
    if len(figures) != 10:
        errors.append({"code": "FIGURE_COUNT", "expected": 10, "actual": len(figures)})
    for figure in figures:
        demo_id = figure["id"]
        stem = figure["stem"]
        folder = root / demo_id
        paths = {
            "pdf": folder / f"{stem}.pdf",
            "svg": folder / f"{stem}.svg",
            "png": folder / f"{stem}.png",
            "contract": folder / "demo_contract.json",
            "summary": folder / "summary.json",
            "layout": folder / "layout_audit.json",
            "data_hashes": folder / "data_hashes.json",
            "artifact_hashes": folder / "artifact_hashes.json",
        }
        row = {"id": demo_id, "stem": stem}
        for name, path in paths.items():
            minimum_bytes = 20 if name == "layout" else 100
            if not path.is_file() or path.stat().st_size < minimum_bytes:
                errors.append({"code": "MISSING_OR_EMPTY", "figure": demo_id, "artifact": name, "path": str(path)})
        if paths["contract"].is_file():
            contract = _load_json(paths["contract"])
            missing = sorted(REQUIRED_CONTRACT_FIELDS - set(contract))
            if missing:
                errors.append({"code": "CONTRACT_FIELDS", "figure": demo_id, "missing": missing})
            if contract.get("synthetic_fixture") is not True or contract.get("contest_evidence_eligible") is not False:
                errors.append({"code": "CONTRACT_EVIDENCE_BOUNDARY", "figure": demo_id})
            if contract.get("backend") != "python" or contract.get("palette_id") != "journal-spectrum-v2":
                errors.append({"code": "CONTRACT_BACKEND_OR_PALETTE", "figure": demo_id})
            if contract.get("min_font_pt", 0) < 8 or contract.get("outputs", {}).get("png_dpi") != 400:
                errors.append({"code": "CONTRACT_EXPORT_QUALITY", "figure": demo_id})
            if len(contract.get("axes", [])) < 2 or not all(item.get("unit") for item in contract.get("axes", [])):
                errors.append({"code": "CONTRACT_AXES", "figure": demo_id})
            if not all(item.get("secondary_encoding") for item in contract.get("color_encoding", [])):
                errors.append({"code": "SECONDARY_ENCODING", "figure": demo_id})
        if paths["layout"].is_file():
            layout = _load_json(paths["layout"])
            row["layout_passed"] = bool(layout.get("passed"))
            if not row["layout_passed"]:
                errors.append({"code": "LAYOUT_AUDIT", "figure": demo_id, "details": layout.get("errors", [])})
        if paths["png"].is_file():
            with Image.open(paths["png"]) as image:
                row["png_pixels"] = [image.width, image.height]
                if image.width < MIN_PNG_WIDTH or image.height < MIN_PNG_HEIGHT:
                    errors.append({"code": "PNG_TOO_SMALL", "figure": demo_id, "size": [image.width, image.height]})
                gray = np.asarray(image.convert("L"))
                dark_fraction = float((gray < 45).mean())
                row["dark_background_fraction"] = round(dark_fraction, 6)
                if dark_fraction > 0.15:
                    errors.append({"code": "DARK_BACKGROUND", "figure": demo_id, "fraction": dark_fraction})
                copy = image.convert("RGB").copy()
                row["visual_salience"] = _raster_salience(copy)
                if row["visual_salience"]["colored_pixel_fraction"] > float(salience_limits["warning_colored_pixel_fraction"]):
                    warnings.append({"code": "COLORED_AREA_HIGH", "figure": demo_id, "fraction": row["visual_salience"]["colored_pixel_fraction"]})
                if row["visual_salience"]["high_saturation_fraction"] > float(salience_limits["warning_high_saturation_fraction"]):
                    warnings.append({"code": "SATURATION_AREA_HIGH", "figure": demo_id, "fraction": row["visual_salience"]["high_saturation_fraction"]})
                images.append((demo_id, copy))
                gray_path = folder / f"{stem}_grayscale.png"
                image.convert("L").save(gray_path, dpi=(400, 400))
                row["grayscale_preview"] = str(gray_path)
        if paths["svg"].is_file():
            text_count = _svg_text_count(paths["svg"])
            row["svg_text_elements"] = text_count
            if text_count < 4:
                errors.append({"code": "SVG_TEXT_NOT_EDITABLE", "figure": demo_id, "text_elements": text_count})
        if paths["pdf"].is_file():
            try:
                pages = len(PdfReader(paths["pdf"]).pages)
            except Exception as exc:  # pypdf provides the detailed parser error
                pages = 0
                errors.append({"code": "PDF_PARSE", "figure": demo_id, "message": str(exc)})
            row["pdf_pages"] = pages
            if pages != 1:
                errors.append({"code": "PDF_PAGE_COUNT", "figure": demo_id, "pages": pages})
            visual = audit_pdf(paths["pdf"], folder / "rendered", dpi)
            (folder / "pdf_visual_audit.json").write_text(json.dumps(visual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            row["pdf_visual_passed"] = bool(visual["passed"])
            if not visual["passed"]:
                errors.extend({"code": item.get("code", "PDF_VISUAL"), "figure": demo_id, "message": item.get("message", "")} for item in visual["errors"])
            warnings.extend({"code": item.get("code", "PDF_VISUAL_WARNING"), "figure": demo_id, "message": item.get("message", "")} for item in visual["warnings"])
        rows.append(row)
    if len(images) == len(figures) and images:
        _contact_sheet(images, root / "contact_sheet_color.png", grayscale=False)
        _contact_sheet(images, root / "contact_sheet_grayscale.png", grayscale=True)
    grayscale = validate_grayscale()
    if not grayscale["passed"]:
        errors.append({"code": "PALETTE_GRAYSCALE", "details": grayscale["checks"]})
    determinism = None
    if reference_root is not None:
        determinism = _compare_runs(root, reference_root, figures)
        if not determinism["passed"]:
            errors.extend(determinism["errors"])
        (root / "determinism_report.json").write_text(json.dumps(determinism, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": 1,
        "suite_id": manifest.get("suite_id"),
        "synthetic_fixture": True,
        "contest_evidence_eligible": False,
        "palette_id": "journal-spectrum-v2",
        "style_profile": "publication-minimal",
        "minimum_png_pixels": [MIN_PNG_WIDTH, MIN_PNG_HEIGHT],
        "passed": not errors,
        "figures": rows,
        "grayscale": grayscale,
        "determinism": determinism,
        "warnings": warnings,
        "errors": errors,
    }
    (root / "suite_visual_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    report = audit_suite(args.root.resolve(), args.dpi, args.reference_root.resolve() if args.reference_root else None)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
