from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
RENDERED = ROOT / "corpus" / "rendered" / "mcm-gmcm"
SELECTION = Path(__file__).with_name("selection.json")

PAGES = {
    "mcm-2006-a-883": [1, 2, 6, 11, 13, 14, 15],
    "mcm-2006-b-868": [1, 8, 9, 10, 12, 19],
    "icm-2006-c-787": [1, 2, 5, 16, 23, 26, 30],
    "mcm-2007-a-1034": [1, 6, 10, 12, 16, 17, 20],
    "mcm-2007-b-2053": [1, 2, 16, 23, 27, 28, 29],
    "icm-2007-c-2052": [1, 4, 6, 7, 9, 16, 21],
    "mcm-2008-a-3694": [1, 6, 17, 20, 23, 25],
    "mcm-2008-b-2858": [1, 2, 10, 11, 16, 17],
    "mcm-2009-a-4339": [1, 5, 9, 16, 20, 21],
    "mcm-2010-a-6749": [1, 5, 16, 39, 43, 44],
    "mcm-2010-b-7273": [1, 4, 9, 10, 16, 17, 18],
    "icm-2010-c-6947": [1, 2, 6, 8, 9, 10],
    "gmcm-2019-a-a19100030004": [1, 2, 8, 14, 24, 26, 38],
    "gmcm-2018-b-b18102520096": [1, 11, 18, 22, 31, 33, 49],
    "gmcm-2020-c-c20102470319": [1, 2, 16, 20, 24, 28, 34],
    "gmcm-2019-d-d19102470244": [1, 2, 14, 22, 26, 29, 30],
    "gmcm-2019-e-e19102840016": [1, 2, 27, 30, 35, 40, 48],
    "gmcm-2018-f-f18100030032": [1, 9, 25, 36, 41, 43, 59],
}


def font(size: int) -> ImageFont.ImageFont:
    candidates = (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def build_sheet(paper_id: str, pages: list[int]) -> None:
    directory = RENDERED / paper_id
    sources = [directory / f"page-{page:02d}.png" for page in pages]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing rendered pages: " + ", ".join(missing))

    thumb_width = 720
    label_height = 48
    gap = 18
    columns = 2
    thumbs: list[tuple[int, Image.Image]] = []
    for page, source in zip(pages, sources, strict=True):
        with Image.open(source) as original:
            rgb = original.convert("RGB")
            height = round(rgb.height * thumb_width / rgb.width)
            thumbs.append((page, rgb.resize((thumb_width, height), Image.Resampling.LANCZOS)))

    cell_height = max(image.height for _, image in thumbs) + label_height
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gap, rows * cell_height + (rows + 1) * gap),
        "#e8e8e8",
    )
    draw = ImageDraw.Draw(sheet)
    label_font = font(26)
    for index, (page, image) in enumerate(thumbs):
        row, column = divmod(index, columns)
        x = gap + column * (thumb_width + gap)
        y = gap + row * cell_height
        sheet.paste(image, (x, y + label_height))
        draw.rectangle((x, y, x + thumb_width, y + label_height), fill="#202020")
        draw.text((x + 14, y + 8), f"{paper_id} | PDF page {page}", fill="white", font=label_font)
    sheet.save(directory / "evidence-review.jpg", quality=93, subsampling=0)


def main() -> None:
    selected = {item["id"] for item in json.loads(SELECTION.read_text(encoding="utf-8"))["papers"]}
    if selected != set(PAGES):
        raise ValueError("The evidence-page map must exactly match selection.json")
    for paper_id, pages in PAGES.items():
        build_sheet(paper_id, pages)
        print(f"{paper_id}: {pages}")


if __name__ == "__main__":
    main()
