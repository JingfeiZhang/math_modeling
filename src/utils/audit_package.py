#!/usr/bin/env python3
"""Deep audit of a CUMCM supporting directory or ZIP archive.

The strict mode is fail-closed for whitelist, path, metadata, and identity
issues.  A directory and the final ZIP are audited with the same rules so a
file cannot pass merely because it was checked before compression.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

# The curated support tree is copied into the ZIP root.  Strict auditing is
# deliberately fail-closed: project internals, paper sources, raw contest
# files, caches, and historical experiment trees are not submission members.
ALLOWED_ROOTS = {"code", "input", "results", "manifest"}
ALLOWED_FILES = {"README.md", "requirements.txt", "run.py"}
BAD_NAMES = {".git", ".codex", ".pytest_cache", "__pycache__", ".support-staging", ".idea"}
ARCHIVES = {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2"}
TEXT_EXTENSIONS = {".tex", ".bib", ".py", ".m", ".yaml", ".yml", ".md", ".txt", ".csv", ".json", ".sh", ".ps1"}
BINARY_TEXT_EXTENSIONS = {".mat", ".bin", ".dat", ".pkl", ".pickle"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
# Decimal output such as ``3.13511675394`` is common in experiment CSV/JSON
# and must not be mistaken for a Chinese mobile number.
PHONE_RE = re.compile(r"(?<![\d.])1[3-9]\d{9}(?![\d.])")
PATH_RE = re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\s\"']+")
LABEL_RE = re.compile(
    r"(?:姓名|学号|队号|指导教师|联系方式|邮箱|email|作者单位|学校|学院)"
    r"\s*[:：=]\s*([^\s,;；}\]]+)",
    re.I,
)
AUTHOR_RE = re.compile(r"\\author\s*\{\s*([^}]*)\}", re.I)
PACKAGE_MANIFEST = "manifest/package_manifest.sha256"


def issue(code: str, message: str, severity: str = "error", **extra: object) -> dict:
    return {"code": code, "message": message, "severity": severity, **extra}


def path_is_bad(raw: str) -> str | None:
    normalized = raw.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", normalized):
        return "absolute path"
    if any(part == ".." for part in path.parts):
        return "path traversal"
    return None


def allowed_member(name: str) -> bool:
    parts = PurePosixPath(name.replace("\\", "/")).parts
    if not parts:
        return False
    if any(part in BAD_NAMES or part.startswith(".") for part in parts):
        return False
    return parts[0] in ALLOWED_ROOTS or (len(parts) == 1 and parts[0] in ALLOWED_FILES)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _find_identity_hits(text: str) -> list[dict]:
    hits: list[dict] = []
    for pattern, label in ((EMAIL_RE, "email"), (PHONE_RE, "phone"), (PATH_RE, "absolute-user-path")):
        for match in pattern.findall(text):
            hits.append({"kind": label, "value": str(match)[:120]})
    for match in LABEL_RE.finditer(text):
        value = match.group(1)
        if value and value not in {"TBD", "待填", "匿名", "None", "null"}:
            hits.append({"kind": "identity-label", "value": match.group(0)[:100]})
    for match in AUTHOR_RE.finditer(text):
        if match.group(1).strip():
            hits.append({"kind": "latex-author", "value": match.group(1).strip()[:100]})
    return hits


def identity_hits(name: str, data: bytes) -> list[dict]:
    """Scan both member names and textual payloads for identity evidence."""

    hits = _find_identity_hits(name.replace("\\", "/"))
    suffix = Path(name).suffix.lower()
    text = _decode_text(data) if suffix in TEXT_EXTENSIONS else ""
    if not text and suffix in BINARY_TEXT_EXTENSIONS:
        printable = re.findall(rb"[ -~\x80-\xff]{4,}", data[:2_000_000])
        text = "\n".join(_decode_text(chunk) for chunk in printable)
    hits.extend(_find_identity_hits(text))
    return hits


def pdf_metadata(name: str, data: bytes) -> list[dict]:
    if not name.lower().endswith(".pdf"):
        return []
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        return [issue("PDF_PARSER_UNAVAILABLE", f"cannot inspect PDF metadata for {name}: {exc}")]
    try:
        reader = PdfReader(io.BytesIO(data))
        metadata = reader.metadata or {}
    except Exception as exc:  # pragma: no cover - parser-specific failures
        return [issue("PDF_PARSE_FAILED", f"cannot parse PDF {name}: {exc}")]
    findings: list[dict] = []
    author = str(metadata.get("/Author", "") or metadata.get("author", "")).strip()
    if author:
        findings.append(issue("PDF_AUTHOR_METADATA", f"{name} contains author metadata: {author[:120]}"))
    for key, value in metadata.items():
        text = str(value or "")
        for hit in _find_identity_hits(text):
            findings.append(issue("PDF_IDENTITY_METADATA", f"{name} metadata {key} contains {hit['kind']}: {hit['value']}"))
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - parser-specific failures
            findings.append(issue("PDF_TEXT_EXTRACTION_FAILED", f"{name} page {page_number}: {exc}"))
            continue
        for hit in _find_identity_hits(text):
            findings.append(issue("PDF_IDENTITY_STRING", f"{name} page {page_number} contains {hit['kind']}: {hit['value']}"))
    return findings


def image_metadata(name: str, data: bytes) -> list[dict]:
    if Path(name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return []
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        suspicious: list[dict] = []
        exif = image.getexif()
        for key, label in ((315, "Artist"), (33432, "Copyright"), (40093, "XPAuthor"), (50741, "OwnerName")):
            if exif.get(key):
                suspicious.append(issue("IMAGE_EXIF_IDENTITY", f"{name} contains {label} metadata"))
        for key, value in image.info.items():
            if isinstance(value, bytes):
                value = _decode_text(value)
            for hit in _find_identity_hits(str(value)):
                suspicious.append(issue("IMAGE_METADATA_IDENTITY", f"{name} metadata {key} contains {hit['kind']}: {hit['value']}"))
        return suspicious
    except Exception:
        return []


def _record_path_policy(name: str, strict: bool, warnings: list[dict], errors: list[dict]) -> None:
    if not allowed_member(name):
        target = errors if strict else warnings
        target.append(issue("OUTSIDE_WHITELIST", f"archive member is outside the supporting whitelist: {name}", "error" if strict else "warning"))


def _record_identity(name: str, data: bytes, errors: list[dict]) -> None:
    for hit in identity_hits(name, data):
        errors.append(issue("IDENTITY_STRING", f"{name} contains {hit['kind']}: {hit['value']}"))


def inspect_zip_bytes(
    data: bytes,
    label: str,
    depth: int,
    entries: list[dict],
    errors: list[dict],
    warnings: list[dict],
    strict: bool,
) -> None:
    if depth > 3:
        errors.append(issue("NESTED_ARCHIVE_DEPTH", f"nested archive depth exceeds 3: {label}"))
        return
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        errors.append(issue("BAD_NESTED_ARCHIVE", f"invalid nested ZIP: {label}"))
        return
    if archive.comment:
        errors.append(issue("ZIP_COMMENT", f"archive contains a non-empty comment: {label}"))
    for member in archive.infolist():
        if member.is_dir():
            continue
        reason = path_is_bad(member.filename)
        if reason:
            errors.append(issue("ZIP_PATH_TRAVERSAL", f"{label}!{member.filename}: {reason}"))
            continue
        nested = archive.read(member)
        full_name = f"{label}!{member.filename}"
        entries.append({"name": full_name, "bytes": len(nested), "depth": depth})
        _record_path_policy(member.filename, strict, warnings, errors)
        _record_identity(full_name, nested, errors)
        if Path(member.filename).suffix.lower() in ARCHIVES:
            errors.append(issue("NESTED_ARCHIVE", f"nested archive is not allowed: {full_name}"))
            if member.filename.lower().endswith(".zip"):
                inspect_zip_bytes(nested, full_name, depth + 1, entries, errors, warnings, strict)
        errors.extend(pdf_metadata(member.filename, nested))
        errors.extend(image_metadata(member.filename, nested))


def inspect_file(name: str, data: bytes, depth: int, entries: list[dict], errors: list[dict], warnings: list[dict], strict: bool) -> None:
    entries.append({"name": name, "bytes": len(data), "depth": depth})
    _record_path_policy(name, strict, warnings, errors)
    _record_identity(name, data, errors)
    if Path(name).suffix.lower() in ARCHIVES:
        errors.append(issue("NESTED_ARCHIVE", f"nested archive is not allowed: {name}"))
        if name.lower().endswith(".zip"):
            inspect_zip_bytes(data, name, depth + 1, entries, errors, warnings, strict)
    errors.extend(pdf_metadata(name, data))
    errors.extend(image_metadata(name, data))


def verify_embedded_manifest(
    payloads: dict[str, bytes], strict: bool, errors: list[dict], warnings: list[dict]
) -> None:
    target = errors if strict else warnings
    severity = "error" if strict else "warning"
    raw = payloads.get(PACKAGE_MANIFEST)
    if raw is None:
        target.append(issue("PACKAGE_MANIFEST_MISSING", f"support package must contain {PACKAGE_MANIFEST}", severity))
        return

    expected: dict[str, str] = {}
    for line_number, line in enumerate(_decode_text(raw).splitlines(), start=1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s{2}(.+)", line.strip())
        if not match:
            target.append(issue("PACKAGE_MANIFEST_FORMAT", f"invalid SHA-256 manifest line {line_number}", severity))
            continue
        name = match.group(2).replace("\\", "/")
        if name == PACKAGE_MANIFEST or path_is_bad(name) or name in expected:
            target.append(issue("PACKAGE_MANIFEST_ENTRY", f"invalid or duplicate manifest member: {name}", severity))
            continue
        expected[name] = match.group(1).lower()

    observed_names = set(payloads) - {PACKAGE_MANIFEST}
    expected_names = set(expected)
    for name in sorted(observed_names - expected_names):
        target.append(issue("PACKAGE_MEMBER_UNLISTED", f"archive member is absent from the embedded manifest: {name}", severity))
    for name in sorted(expected_names - observed_names):
        target.append(issue("PACKAGE_MEMBER_MISSING", f"embedded manifest references a missing member: {name}", severity))
    for name in sorted(observed_names & expected_names):
        digest = hashlib.sha256(payloads[name]).hexdigest()
        if digest != expected[name]:
            target.append(issue("PACKAGE_HASH_MISMATCH", f"SHA-256 mismatch for package member: {name}", severity))


def audit(source: Path, strict: bool = False) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    info: list[dict] = []
    entries: list[dict] = []
    payloads: dict[str, bytes] = {}
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            reason = path_is_bad(relative)
            if reason:
                errors.append(issue("PATH_TRAVERSAL", f"{relative}: {reason}"))
                continue
            data = path.read_bytes()
            payloads[relative] = data
            inspect_file(relative, data, 0, entries, errors, warnings, strict)
    elif source.is_file() and source.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(source) as archive:
                if archive.comment:
                    errors.append(issue("ZIP_COMMENT", f"archive contains a non-empty comment: {source.name}"))
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    reason = path_is_bad(member.filename)
                    if reason:
                        errors.append(issue("ZIP_PATH_TRAVERSAL", f"{member.filename}: {reason}"))
                        continue
                    data = archive.read(member)
                    normalized = member.filename.replace("\\", "/")
                    payloads[normalized] = data
                    inspect_file(normalized, data, 0, entries, errors, warnings, strict)
        except zipfile.BadZipFile:
            errors.append(issue("BAD_ZIP", f"invalid ZIP archive: {source}"))
    else:
        errors.append(issue("SOURCE_MISSING", f"supporting source does not exist: {source}"))
    if payloads:
        verify_embedded_manifest(payloads, strict, errors, warnings)
    info.append({"code": "ENTRY_COUNT", "message": f"inspected {len(entries)} file entries"})
    return {
        "schema_version": 3,
        "source": str(source),
        "strict": strict,
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "metrics": {"entries": len(entries)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true", help="turn whitelist warnings into blocking errors")
    args = parser.parse_args()
    result = audit(args.source.resolve(), strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
