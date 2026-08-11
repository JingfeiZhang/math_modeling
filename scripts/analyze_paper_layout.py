from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "corpus" / "raw"
RENDERED_ROOT = ROOT / "corpus" / "rendered"


def resolve_manifest_page(manifest_path: Path, page: dict[str, object]) -> Path | None:
    """Resolve both repository-root paths and legacy per-paper basenames."""
    raw = Path(str(page.get("file", "")))
    candidates = [raw if raw.is_absolute() else ROOT / raw, manifest_path.parent / raw]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def content_metrics(image: Image.Image) -> dict[str, float | int]:
    rgb = np.asarray(image.convert("RGB"))
    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    analysis_height = int(height * 0.9)  # Exclude the official site's pale watermark area.
    gray_body = gray[:analysis_height]
    rgb_body = rgb[:analysis_height]
    ink = gray_body < 200
    ys, xs = np.where(ink)
    if len(xs):
        left, right = int(xs.min()), int(xs.max())
        top, bottom = int(ys.min()), int(ys.max())
    else:
        left, right, top, bottom = 0, width - 1, 0, analysis_height - 1

    channel_range = rgb_body.max(axis=2).astype(np.int16) - rgb_body.min(axis=2).astype(np.int16)
    colored = (channel_range > 18) & (rgb_body.min(axis=2) < 235)
    return {
        "width_px": width,
        "height_px": height,
        "ink_density": float(ink.mean()),
        "color_pixel_fraction": float(colored.mean()),
        "left_margin_ratio": left / width,
        "right_margin_ratio": (width - 1 - right) / width,
        "top_margin_ratio": top / height,
        "bottom_margin_ratio": (analysis_height - 1 - bottom) / height,
    }


def contact_sheet(
    paper_id: str,
    images: list[Path],
    start_page: int,
    destination: Path,
) -> None:
    thumb_width, thumb_height = 245, 346
    label_height = 26
    columns, rows = 5, 2
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "#D9D9D9")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, path in enumerate(images):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_width - 8, thumb_height - 8), Image.Resampling.LANCZOS)
        column, row = index % columns, index // columns
        x = column * thumb_width + (thumb_width - image.width) // 2
        y = row * (thumb_height + label_height) + 4
        sheet.paste(image, (x, y))
        label = f"{paper_id}  p.{start_page + index:02d}"
        draw.text(
            (column * thumb_width + 8, row * (thumb_height + label_height) + thumb_height + 5),
            label,
            fill="#111111",
            font=font,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=94)


def main() -> None:
    RENDERED_ROOT.mkdir(parents=True, exist_ok=True)
    metric_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for manifest_path in sorted(RAW_ROOT.glob("*/source_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paper_id = manifest_path.parent.name
        problem = manifest.get("problem") or manifest.get("problem_id") or ""
        manifest_pages = manifest.get("pages") or manifest.get("render", {}).get("pages", [])
        resolved_pages = []
        for page in manifest_pages:
            path = resolve_manifest_page(manifest_path, page)
            if path is not None:
                resolved_pages.append((int(page.get("page", len(resolved_pages) + 1)), path))
        page_paths = [path for _, path in sorted(resolved_pages, key=lambda item: item[0])]
        if not page_paths:
            continue
        paper_metrics: list[dict[str, object]] = []
        for page_path in page_paths:
            page_number = int(page_path.stem.rsplit("-", maxsplit=1)[-1])
            with Image.open(page_path) as image:
                metrics: dict[str, object] = {
                    "paper_id": paper_id,
                    "problem": problem,
                    "page": page_number,
                    **content_metrics(image),
                }
            metric_rows.append(metrics)
            paper_metrics.append(metrics)

        for offset in range(0, len(page_paths), 10):
            chunk = page_paths[offset : offset + 10]
            contact_sheet(
                paper_id,
                chunk,
                offset + 1,
                RENDERED_ROOT / paper_id / f"contact-{offset + 1:02d}-{offset + len(chunk):02d}.jpg",
            )

        numeric_keys = (
            "ink_density",
            "color_pixel_fraction",
            "left_margin_ratio",
            "right_margin_ratio",
            "top_margin_ratio",
            "bottom_margin_ratio",
        )
        summary: dict[str, object] = {
            "paper_id": paper_id,
            "problem": problem,
            "cached_pages": len(page_paths),
        }
        for key in numeric_keys:
            values = np.asarray([float(row[key]) for row in paper_metrics])
            summary[f"median_{key}"] = float(np.median(values))
        summary_rows.append(summary)

    metric_path = ROOT / "corpus" / "layout_metrics.csv"
    with metric_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)

    summary_path = ROOT / "corpus" / "layout_summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(metric_path)
    print(summary_path)
    print(RENDERED_ROOT)


if __name__ == "__main__":
    main()
