from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from src.utils import audit_pdf_visual


def _draw_lines(path: Path, ranges: list[tuple[int, int]]) -> None:
    image = Image.new("L", (1000, 1400), 255)
    draw = ImageDraw.Draw(image)
    for start, end in ranges:
        for y in range(start, end, 35):
            draw.rectangle((100, y, 900, y + 9), fill=0)
    image.save(path)


def test_detects_half_page_and_internal_whitespace(tmp_path: Path) -> None:
    half = tmp_path / "half.png"
    _draw_lines(half, [(150, 500)])
    half_metrics = audit_pdf_visual.image_metrics(half)
    half_codes = {item["code"] for item in audit_pdf_visual.page_flow_warnings(half_metrics, 1, 300)}
    assert "HALF_PAGE_WHITESPACE" in half_codes

    internal = tmp_path / "internal.png"
    _draw_lines(internal, [(150, 430), (950, 1200)])
    internal_metrics = audit_pdf_visual.image_metrics(internal)
    internal_codes = {item["code"] for item in audit_pdf_visual.page_flow_warnings(internal_metrics, 2, 300)}
    assert "INTERNAL_WHITESPACE_BAND" in internal_codes


def test_detects_heading_orphaned_at_page_bottom() -> None:
    words = [
        {"text": "正文", "xMin": 80.0, "yMin": 200.0, "xMax": 110.0, "yMax": 209.0, "height": 9.0},
        {"text": "模型评价与推广", "xMin": 80.0, "yMin": 650.0, "xMax": 190.0, "yMax": 664.0, "height": 14.0},
        {"text": "短句", "xMin": 80.0, "yMin": 690.0, "xMax": 110.0, "yMax": 699.0, "height": 9.0},
    ]
    result = audit_pdf_visual.orphan_heading_warnings(
        [{"page": 3, "width": 600.0, "height": 800.0, "words": words}]
    )
    assert result
    assert result[0]["code"] == "ORPHAN_HEADING"
    assert result[0]["page"] == 3


def test_does_not_flag_heading_with_following_paragraph() -> None:
    words = [
        {"text": "3.2模型建立", "xMin": 80.0, "yMin": 620.0, "xMax": 180.0, "yMax": 634.0, "height": 14.0},
    ]
    for index in range(5):
        words.append(
            {
                "text": "这是完整的正文说明并包含足够内容",
                "xMin": 80.0,
                "yMin": 650.0 + index * 18,
                "xMax": 300.0,
                "yMax": 659.0 + index * 18,
                "height": 9.0,
            }
        )
    result = audit_pdf_visual.orphan_heading_warnings(
        [{"page": 4, "width": 600.0, "height": 800.0, "words": words}]
    )
    assert result == []
