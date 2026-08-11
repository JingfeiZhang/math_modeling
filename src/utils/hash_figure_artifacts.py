from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_svg_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<metadata\b.*?</metadata>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"fillPattern[0-9]+_", "fillPattern_", text)
    text = "\n".join(line.rstrip(" \t") for line in text.split("\n")).strip()
    return text.encode("utf-8")


def png_pixel_payload(path: Path) -> tuple[bytes, int, int]:
    from PIL import Image

    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        header = f"RGBA|{width}x{height}|uint8|".encode("ascii")
        return header + rgba.tobytes(), width, height


def build_manifest(directory: Path, stem: str) -> dict:
    pdf = directory / f"{stem}.pdf"
    svg = directory / f"{stem}.svg"
    png = directory / f"{stem}.png"
    for path in (pdf, svg, png):
        if not path.is_file():
            raise FileNotFoundError(path)

    pixel_payload, width, height = png_pixel_payload(png)
    return {
        "schema_version": 1,
        "stem": stem,
        "artifacts": {
            "pdf": {
                "path": str(pdf),
                "bytes": pdf.stat().st_size,
                "raw_sha256": raw_sha256(pdf),
                "determinism_role": "provenance-only",
            },
            "svg": {
                "path": str(svg),
                "bytes": svg.stat().st_size,
                "raw_sha256": raw_sha256(svg),
                "canonical_sha256": hashlib.sha256(canonical_svg_bytes(svg)).hexdigest(),
                "canonicalization": "utf8-lf-no-comments-no-metadata-fillpattern-normalized-rstrip",
            },
            "png": {
                "path": str(png),
                "bytes": png.stat().st_size,
                "raw_sha256": raw_sha256(png),
                "pixel_sha256": hashlib.sha256(pixel_payload).hexdigest(),
                "pixel_encoding": f"RGBA|{width}x{height}|uint8|row-major",
            },
        },
        "reproducibility_note": (
            "PDF raw SHA-256 is retained for provenance, but export metadata may change raw bytes. "
            "Use canonical SVG SHA-256 and decoded PNG pixel SHA-256 as deterministic visual checks."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash a MATLAB PDF/SVG/PNG figure triplet.")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--stem", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.directory.resolve(), args.stem)
    output = args.output or args.directory / f"{args.stem}.hashes.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
