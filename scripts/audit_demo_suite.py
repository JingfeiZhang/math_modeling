"""Visual QA and contact sheets for the synthetic MATLAB figure suite."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.utils.audit_pdf_visual import audit as audit_pdf  # noqa: E402

DEMOS = [
    ("fig-01-prediction-interval", "prediction_interval"),
    ("fig-02-calibration", "calibration"),
    ("fig-03-residual-diagnostics", "residual_diagnostics"),
    ("fig-04-pareto-frontier", "pareto_frontier"),
    ("fig-05-optimization-convergence", "convergence"),
    ("fig-06-resource-allocation", "allocation"),
    ("fig-07-sensitivity-ranking", "sensitivity_ranking"),
    ("fig-08-robustness-matrix", "robustness_matrix"),
    ("fig-09-uncertainty-distribution", "uncertainty_distribution"),
    ("fig-10-spatial-risk-field", "spatial_risk_field"),
    ("fig-11-network-routes", "network_routes"),
    ("fig-12-service-comparison", "service_comparison"),
]
MIN_PNG_WIDTH = 1100
MIN_PNG_HEIGHT = 700


def make_contact_sheet(images: list[Image.Image], output: Path, grayscale: bool) -> None:
    thumb_w, thumb_h = 780, 590
    columns = 4
    rows = (len(images) + columns - 1) // columns
    canvas = Image.new("RGB", (thumb_w * columns, thumb_h * rows), "white")
    for index, source in enumerate(images):
        image = source.convert("L").convert("RGB") if grayscale else source.convert("RGB")
        image.thumbnail((thumb_w - 30, thumb_h - 30), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb_w, thumb_h), "white")
        left = (thumb_w - image.width) // 2
        top = (thumb_h - image.height) // 2
        tile.paste(image, (left, top))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, thumb_w - 1, thumb_h - 1), outline="#D9DEE5", width=2)
        canvas.paste(tile, ((index % columns) * thumb_w, (index // columns) * thumb_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, dpi=(150, 150))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    root = args.root.resolve()
    rows: list[dict] = []
    images: list[Image.Image] = []
    errors: list[dict] = []
    for demo_id, stem in DEMOS:
        folder = root / demo_id
        png = folder / f"{stem}.png"
        pdf = folder / f"{stem}.pdf"
        svg = folder / f"{stem}.svg"
        row = {"id": demo_id, "png": str(png), "pdf": str(pdf), "svg": str(svg)}
        for path in (png, pdf, svg, folder / "demo_contract.json", folder / "data_hashes.json"):
            if not path.is_file() or path.stat().st_size < 100:
                errors.append({"code": "MISSING_OR_EMPTY", "path": str(path)})
        if png.is_file():
            with Image.open(png) as image:
                row["png_width"], row["png_height"] = image.size
                gray = image.convert("L")
                import numpy as np
                dark_fraction = float((np.asarray(gray) < 45).mean())
                row["dark_background_fraction"] = round(dark_fraction, 5)
                if dark_fraction > 0.35:
                    errors.append({"code": "DARK_BACKGROUND", "path": str(png), "fraction": dark_fraction})
                if image.width < MIN_PNG_WIDTH or image.height < MIN_PNG_HEIGHT:
                    errors.append({"code": "PNG_TOO_SMALL", "path": str(png), "size": list(image.size)})
                images.append(image.copy())
                gray_path = folder / f"{stem}_grayscale.png"
                image.convert("L").save(gray_path, dpi=(400, 400))
                row["grayscale"] = str(gray_path)
        visual_path = folder / "pdf_visual_audit.json"
        if pdf.is_file():
            visual = audit_pdf(pdf, folder / "rendered", args.dpi)
            visual_path.write_text(json.dumps(visual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            row["pdf_visual_passed"] = bool(visual["passed"])
            if not visual["passed"]:
                errors.extend(
                    {"code": item.get("code", "PDF_VISUAL"), "message": item.get("message", ""), "demo": demo_id}
                    for item in visual["errors"]
                )
        row["visual_audit"] = str(visual_path)
        rows.append(row)
    if len(images) == len(DEMOS):
        make_contact_sheet(images, root / "contact_sheet_color.png", grayscale=False)
        make_contact_sheet(images, root / "contact_sheet_grayscale.png", grayscale=True)
    report = {
        "schema_version": 2,
        "synthetic_fixture": True,
        "passed": not errors,
        "minimum_png_pixels": [MIN_PNG_WIDTH, MIN_PNG_HEIGHT],
        "demos": rows,
        "errors": errors,
    }
    (root / "suite_visual_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
