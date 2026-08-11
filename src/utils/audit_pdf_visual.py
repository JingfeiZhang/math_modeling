#!/usr/bin/env python3
"""Render and inspect a submission PDF for layout defects."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def pdf_pages(pdf: Path) -> int | None:
    result = run(["pdfinfo", str(pdf)])
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
    return int(match.group(1)) if result.returncode == 0 and match else None


def text_pages(pdf: Path) -> list[str]:
    result = run(["pdftotext", "-layout", str(pdf), "-"])
    return result.stdout.split("\f") if result.returncode == 0 else []


def word_boxes(pdf: Path) -> tuple[list[dict], list[dict]]:
    result = run(["pdftotext", "-bbox-layout", str(pdf), "-"])
    if result.returncode != 0:
        return [], [{"code": "BBOX_EXTRACT_FAILED", "message": result.stderr.strip()}]
    xml_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", result.stdout)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return [], [{"code": "BBOX_PARSE_FAILED", "message": str(exc)}]
    pages: list[dict] = []
    page_nodes = root.findall(".//page") or root.findall(".//{*}page")
    for index, page in enumerate(page_nodes, start=1):
        words: list[dict] = []
        word_nodes = page.findall(".//word") or page.findall(".//{*}word")
        for word in word_nodes:
            try:
                box = {key: float(word.attrib[key]) for key in ("xMin", "yMin", "xMax", "yMax")}
            except (KeyError, ValueError):
                continue
            words.append({"text": "".join(word.itertext()), **box, "height": box["yMax"] - box["yMin"]})
        pages.append({"page": index, "width": float(page.attrib.get("width", 0)), "height": float(page.attrib.get("height", 0)), "words": words})
    return pages, []


def fonts(pdf: Path) -> tuple[list[dict], list[dict]]:
    result = run(["pdffonts", str(pdf)])
    if result.returncode != 0:
        return [], [{"code": "FONT_INSPECTION_FAILED", "message": result.stderr.strip()}]
    rows: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip() or line.startswith("name") or line.strip().startswith("-"):
            continue
        parts = line.split()
        flags = [part.lower() for part in parts[1:] if part.lower() in {"yes", "no"}]
        if len(flags) < 3:
            continue
        rows.append({"name": parts[0], "embedded": flags[0] == "yes", "subset": flags[1] == "yes", "unicode": flags[2] == "yes", "raw": line})
    return rows, []


def render(pdf: Path, destination: Path, dpi: int) -> tuple[list[Path], list[dict]]:
    destination.mkdir(parents=True, exist_ok=True)
    for old in destination.glob("page-*.png"):
        old.unlink()
    executable = shutil.which("pdftoppm")
    if not executable:
        return [], [{"code": "RENDERER_MISSING", "message": "pdftoppm was not found"}]
    if executable.lower().endswith((".cmd", ".bat")):
        native = (Path(executable).parent / ".." / ".." / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe").resolve()
        if native.is_file():
            executable = str(native)
    render_args = ["-png", "-r", str(dpi), str(pdf), str(destination / "page")]
    if executable.lower().endswith((".cmd", ".bat")):
        command = ["cmd.exe", "/d", "/s", "/c", "call " + subprocess.list2cmdline([executable, *render_args])]
    else:
        command = [executable, *render_args]
    result = run(command)
    if result.returncode != 0:
        return [], [{"code": "RENDER_FAILED", "message": result.stderr.strip()}]
    return sorted(destination.glob("page-*.png")), []


def image_metrics(path: Path) -> dict:
    from PIL import Image
    import numpy as np

    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"))
    ink = gray < 245
    height, width = gray.shape
    ys, xs = np.where(ink)
    if not len(xs):
        return {
            "width_px": width,
            "height_px": height,
            "ink_fraction": 0.0,
            "bbox": None,
            "edge_ink_fraction": 0.0,
            "body_top_blank_fraction": 1.0,
            "body_bottom_blank_fraction": 1.0,
            "largest_internal_blank_fraction": 1.0,
        }
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    border = np.zeros_like(ink)
    border[:3, :] = True
    border[-3:, :] = True
    border[:, :3] = True
    border[:, -3:] = True
    x0, x1 = int(width * 0.08), max(int(width * 0.92), int(width * 0.08) + 1)
    y0, y1 = int(height * 0.08), max(int(height * 0.92), int(height * 0.08) + 1)
    body = ink[y0:y1, x0:x1]
    row_fraction = body.mean(axis=1) if body.size else np.zeros(0, dtype=float)
    active = row_fraction > 0.0015
    # Bridge normal inter-line spacing without hiding paragraph- or float-sized gaps.
    bridge = max(1, int(height * 0.012))
    if active.size:
        active = np.convolve(active.astype(np.uint8), np.ones(bridge, dtype=np.uint8), mode="same") > 0
    active_rows = np.flatnonzero(active)
    if not active_rows.size:
        top_blank = bottom_blank = largest_internal = 1.0
    else:
        body_height = len(active)
        first, last = int(active_rows[0]), int(active_rows[-1])
        top_blank = first / max(body_height, 1)
        bottom_blank = (body_height - last - 1) / max(body_height, 1)
        inactive = ~active[first:last + 1]
        padded = np.concatenate(([False], inactive, [False]))
        transitions = np.diff(padded.astype(np.int8))
        starts = np.flatnonzero(transitions == 1)
        ends = np.flatnonzero(transitions == -1)
        largest_internal = (int((ends - starts).max()) / max(body_height, 1)) if len(starts) else 0.0
    return {
        "width_px": width,
        "height_px": height,
        "ink_fraction": float(ink.mean()),
        "bbox": bbox,
        "edge_ink_fraction": float((ink & border).mean()),
        "body_top_blank_fraction": float(top_blank),
        "body_bottom_blank_fraction": float(bottom_blank),
        "largest_internal_blank_fraction": float(largest_internal),
    }


def page_flow_warnings(metrics: dict, page: int, text_chars: int) -> list[dict]:
    if metrics.get("bbox") is None or text_chars < 20:
        return []
    warnings: list[dict] = []
    top_blank = float(metrics.get("body_top_blank_fraction", 0.0))
    bottom_blank = float(metrics.get("body_bottom_blank_fraction", 0.0))
    internal_blank = float(metrics.get("largest_internal_blank_fraction", 0.0))
    if max(top_blank, bottom_blank) >= 0.42:
        location = "top" if top_blank >= bottom_blank else "bottom"
        warnings.append(
            {
                "code": "HALF_PAGE_WHITESPACE",
                "message": f"page {page} leaves approximately half of the body blank at the {location}",
                "page": page,
                "location": location,
                "fraction": round(max(top_blank, bottom_blank), 4),
            }
        )
    elif max(top_blank, bottom_blank) >= 0.30:
        location = "top" if top_blank >= bottom_blank else "bottom"
        warnings.append(
            {
                "code": "LARGE_TERMINAL_WHITESPACE",
                "message": f"page {page} has a large blank body region at the {location}",
                "page": page,
                "location": location,
                "fraction": round(max(top_blank, bottom_blank), 4),
            }
        )
    if internal_blank >= 0.20:
        warnings.append(
            {
                "code": "INTERNAL_WHITESPACE_BAND",
                "message": f"page {page} contains a large internal horizontal whitespace band",
                "page": page,
                "fraction": round(internal_blank, 4),
            }
        )
    return warnings


def _word_lines(page: dict) -> list[dict]:
    lines: list[dict] = []
    for word in sorted(page.get("words", []), key=lambda item: (item["yMin"], item["xMin"])):
        line = next((candidate for candidate in reversed(lines[-3:]) if abs(candidate["yMin"] - word["yMin"]) <= 2.0), None)
        if line is None:
            line = {"yMin": word["yMin"], "yMax": word["yMax"], "words": []}
            lines.append(line)
        line["words"].append(word)
        line["yMax"] = max(line["yMax"], word["yMax"])
    for line in lines:
        line["words"].sort(key=lambda item: item["xMin"])
        line["text"] = "".join(item["text"] for item in line["words"]).strip()
        line["height"] = max((item["height"] for item in line["words"]), default=0.0)
    return lines


def orphan_heading_warnings(box_pages: list[dict]) -> list[dict]:
    warnings: list[dict] = []
    heading_text = re.compile(
        r"^(?:第?[一二三四五六七八九十\d]+(?:[.．、]\d+)*[\s　]*|)"
        r"(?:问题重述|问题分析|模型假设|符号约定|数据处理|问题[一二三四五六七八九十\d]+|模型评价|参考文献|附录)"
    )
    numbered_heading = re.compile(r"^\d+(?:\.\d+){0,3}\s*[^\d\s].{0,40}$")
    for page in box_pages:
        lines = _word_lines(page)
        word_heights = sorted(word["height"] for word in page.get("words", []) if word["height"] > 0)
        if not lines or not word_heights or page.get("height", 0) <= 0:
            continue
        median = word_heights[len(word_heights) // 2]
        for index, line in enumerate(lines):
            text = re.sub(r"\s+", "", line.get("text", ""))
            if line["yMin"] < page["height"] * 0.76:
                continue
            if line["height"] < max(10.5, median * 1.08):
                continue
            if not (heading_text.search(text) or numbered_heading.search(text)):
                continue
            following = [candidate for candidate in lines[index + 1:] if candidate["yMin"] < page["height"] * 0.94]
            following_text = "".join(candidate["text"] for candidate in following)
            if len(re.sub(r"\s+", "", following_text)) < 45 or len(following) < 3:
                warnings.append(
                    {
                        "code": "ORPHAN_HEADING",
                        "message": f"page {page['page']} ends with a heading and too little following text: {text[:60]}",
                        "page": page["page"],
                        "heading": text[:120],
                    }
                )
                break
    return warnings


def audit(pdf: Path, render_dir: Path, dpi: int) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    info: list[dict] = []
    if not pdf.is_file():
        errors.append({"code": "PDF_MISSING", "message": str(pdf)})
        return {"schema_version": 1, "passed": False, "errors": errors, "warnings": warnings, "info": info, "metrics": {}}
    page_count = pdf_pages(pdf)
    texts = text_pages(pdf)
    rendered, render_errors = render(pdf, render_dir, dpi)
    errors.extend(render_errors)
    pages: list[dict] = []
    for index, path in enumerate(rendered, start=1):
        metrics = image_metrics(path)
        text = texts[index - 1] if index - 1 < len(texts) else ""
        row = {"page": index, "file": str(path), "text_chars": len(re.sub(r"\s+", "", text)), **metrics}
        pages.append(row)
        if metrics["bbox"] is None or (metrics["ink_fraction"] < 0.0005 and row["text_chars"] < 20):
            errors.append({"code": "BLANK_PAGE", "message": f"page {index} is blank or nearly blank"})
        elif metrics["bbox"] and metrics["edge_ink_fraction"] > 0.002 and any(value <= 3 for value in (metrics["bbox"][0], metrics["bbox"][1], metrics["width_px"] - metrics["bbox"][2] - 1, metrics["height_px"] - metrics["bbox"][3] - 1)):
            errors.append({"code": "SEVERE_CROP", "message": f"page {index} has ink touching the render edge"})
        elif metrics["ink_fraction"] < 0.012:
            warnings.append({"code": "EXCESSIVE_WHITESPACE", "message": f"page {index} has unusually low ink density", "page": index})
        warnings.extend(page_flow_warnings(metrics, index, row["text_chars"]))
    boxes, box_errors = word_boxes(pdf)
    errors.extend(box_errors)
    small_words = 0
    overlaps: list[dict] = []
    for page in boxes:
        words = page["words"]
        small_words += sum(1 for word in words if 0 < word["height"] < 6.5)
        ordered = sorted(words, key=lambda item: (item["yMin"], item["xMin"]))
        for left, right in zip(ordered, ordered[1:]):
            intersection = max(0.0, min(left["xMax"], right["xMax"]) - max(left["xMin"], right["xMin"])) * max(0.0, min(left["yMax"], right["yMax"]) - max(left["yMin"], right["yMin"]))
            area = min((left["xMax"] - left["xMin"]) * (left["yMax"] - left["yMin"]), (right["xMax"] - right["xMin"]) * (right["yMax"] - right["yMin"]))
            if area > 0 and intersection / area > 0.35 and left["text"] != right["text"]:
                overlaps.append({"page": page["page"], "left": left["text"], "right": right["text"]})
                if len(overlaps) >= 20:
                    break
    if small_words > 20:
        warnings.append({"code": "SMALL_TEXT", "message": f"{small_words} word boxes are below approximately 6.5pt"})
    if overlaps:
        warnings.append({"code": "TEXT_BOX_OVERLAP", "message": f"{len(overlaps)} possible overlapping text boxes", "examples": overlaps[:5]})
    warnings.extend(orphan_heading_warnings(boxes))
    font_rows, font_errors = fonts(pdf)
    errors.extend(font_errors)
    unembedded = [row["name"] for row in font_rows if not row["embedded"]]
    if unembedded:
        errors.append({"code": "FONT_NOT_EMBEDDED", "message": "unembedded fonts: " + ", ".join(unembedded)})
    info.append({"code": "RENDERED_PAGES", "message": f"rendered {len(rendered)} page(s) at {dpi} dpi"})
    return {"schema_version": 1, "passed": not errors, "errors": errors, "warnings": warnings, "info": info, "metrics": {"page_count": page_count, "rendered_pages": len(rendered), "fonts": font_rows, "pages": pages, "render_dir": str(render_dir)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--render-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    result = audit(args.pdf.resolve(), args.render_dir.resolve(), args.dpi)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
