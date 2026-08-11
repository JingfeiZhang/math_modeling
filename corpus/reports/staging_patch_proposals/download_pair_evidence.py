from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any


COMMIT = "8783d0d822f89f98aa6182dd933cc2e9f3e2ddce"
REPOSITORY = "https://github.com/personqianduixue/Math_Model"
SOURCE_ROOT = "2-1国赛题目+论文/"
DATA_EXTENSIONS = {".csv", ".dat", ".mat", ".txt", ".xls", ".xlsx"}
FIGURE_EXTENSIONS = {".fig", ".jpg", ".png"}


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def candidate_id(prefix: str) -> str:
    parts = PurePosixPath(prefix).parts
    year = parts[1]
    team = re.sub(r"[^a-z0-9]+", "-", parts[2].casefold()).strip("-")
    return f"cumcm-{year}-{team}"


def select_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        path = str(entry.get("path", ""))
        parts = PurePosixPath(path).parts
        if not path.startswith(SOURCE_ROOT) or len(parts) < 3:
            continue
        prefix = "/".join(parts[:3])
        groups[prefix].append(entry)

    candidates: list[dict[str, Any]] = []
    for prefix, group in sorted(groups.items()):
        pdfs = [item for item in group if item.get("extension") == ".pdf"]
        matlab = [item for item in group if item.get("extension") == ".m"]
        if len(pdfs) != 1 or not matlab:
            continue
        data = sorted(
            [
                item
                for item in group
                if item.get("extension") in DATA_EXTENSIONS
                and 0 < int(item.get("bytes", 0)) <= 2_000_000
            ],
            key=lambda item: (int(item.get("bytes", 0)), item["path"]),
        )[:8]
        figures = sorted(
            [
                item
                for item in group
                if item.get("extension") in FIGURE_EXTENSIONS
                and 0 < int(item.get("bytes", 0)) <= 1_000_000
            ],
            key=lambda item: (int(item.get("bytes", 0)), item["path"]),
        )[:3]
        representative_matlab = sorted(
            matlab,
            key=lambda item: (-int(item.get("bytes", 0)), item["path"]),
        )[:2]
        candidates.append(
            {
                "candidate_id": candidate_id(prefix),
                "prefix": prefix,
                "pdf": pdfs[0],
                "matlab": representative_matlab,
                "data": data,
                "figures": figures,
                "total_group_entries": len(group),
            }
        )
    return candidates


def raw_url(path: str) -> str:
    encoded = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/personqianduixue/Math_Model/{COMMIT}/{encoded}"


def blob_url(blob_sha: str) -> str:
    return f"https://api.github.com/repos/personqianduixue/Math_Model/git/blobs/{blob_sha}"


def fetch(entry: dict[str, Any], attempts: int = 4) -> tuple[dict[str, Any], bytes]:
    url = blob_url(str(entry["blob_sha"]))
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github.raw+json",
                "User-Agent": "math-modeling-paper-miner/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read()
            if content.lstrip().startswith(b"{") and b'"content"' in content[:500]:
                raise ValueError("GitHub API returned JSON instead of raw blob")
            expected_bytes = int(entry["bytes"])
            if len(content) != expected_bytes:
                raise ValueError(
                    f"byte mismatch for {entry['path']}: {len(content)} != {expected_bytes}"
                )
            observed_blob = git_blob_sha1(content)
            if observed_blob != entry["blob_sha"]:
                raise ValueError(
                    f"blob mismatch for {entry['path']}: {observed_blob} != {entry['blob_sha']}"
                )
            return entry, content
        except Exception as exc:  # Network failures are recorded, never hidden.
            error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    assert error is not None
    raise error


def fetch_local(entry: dict[str, Any], checkout_root: Path) -> tuple[dict[str, Any], bytes]:
    relative = PurePosixPath(str(entry["path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe source path: {entry['path']}")
    source = checkout_root.joinpath(*relative.parts)
    if not source.is_file():
        raise FileNotFoundError(source)
    content = source.read_bytes()
    expected_bytes = int(entry["bytes"])
    if len(content) != expected_bytes:
        raise ValueError(f"byte mismatch for {entry['path']}: {len(content)} != {expected_bytes}")
    observed_blob = git_blob_sha1(content)
    if observed_blob != entry["blob_sha"]:
        raise ValueError(
            f"blob mismatch for {entry['path']}: {observed_blob} != {entry['blob_sha']}"
        )
    return entry, content


def safe_extension(entry: dict[str, Any]) -> str:
    extension = str(entry.get("extension", "")).casefold()
    if not re.fullmatch(r"\.[a-z0-9_-]{1,8}", extension):
        return ".bin"
    return extension


def write_object(root: Path, entry: dict[str, Any], content: bytes) -> dict[str, Any]:
    digest = sha256(content)
    extension = safe_extension(entry)
    target = root / "objects" / "sha256" / digest[:2] / f"{digest}{extension}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        prior = target.read_bytes()
        if sha256(prior) != digest:
            raise ValueError(f"content-addressed object is corrupt: {target}")
    else:
        target.write_bytes(content)
    return {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "path": entry["path"],
        "raw_url": raw_url(str(entry["path"])),
        "blob_url": blob_url(str(entry["blob_sha"])),
        "blob_sha": entry["blob_sha"],
        "expected_bytes": int(entry["bytes"]),
        "sha256": digest,
        "object": target.relative_to(root.parent.parent).as_posix(),
        "downloaded": date.today().isoformat(),
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--checkout-root", type=Path)
    parser.add_argument("--emit-sparse", type=Path)
    parser.add_argument("--emit-sparse-only", action="store_true")
    args = parser.parse_args()

    tree = json.loads(args.tree.read_text(encoding="utf-8"))
    if tree.get("commit") != COMMIT or tree.get("truncated") is not False:
        raise ValueError("source tree is not the complete pinned commit")
    candidates = select_candidates(list(tree["entries"]))
    args.output.mkdir(parents=True, exist_ok=True)

    unique_entries: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        for role in ("pdf",):
            entry = candidate[role]
            unique_entries.setdefault(entry["blob_sha"], entry)
        for role in ("matlab",):
            for entry in candidate[role]:
                unique_entries.setdefault(entry["blob_sha"], entry)

    if args.emit_sparse:
        args.emit_sparse.parent.mkdir(parents=True, exist_ok=True)
        sparse_lines = ["/*", "!/*/"]
        parents: set[PurePosixPath] = set()
        for entry in unique_entries.values():
            parent = PurePosixPath(str(entry["path"])).parent
            while parent.parts:
                parents.add(parent)
                parent = parent.parent
        for parent in sorted(parents, key=lambda item: (len(item.parts), item.as_posix())):
            path = parent.as_posix()
            sparse_lines.extend((f"/{path}/", f"!/{path}/*/"))
        sparse_lines.extend(
            f"/{entry['path']}" for entry in sorted(unique_entries.values(), key=lambda item: item["path"])
        )
        args.emit_sparse.write_text("\n".join(sparse_lines) + "\n", encoding="utf-8")

    if args.emit_sparse_only:
        if args.emit_sparse is None:
            raise ValueError("--emit-sparse-only requires --emit-sparse")
        print(
            json.dumps(
                {
                    "candidate_count": len(candidates),
                    "unique_blob_count": len(unique_entries),
                    "sparse_file": str(args.emit_sparse),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.checkout_root is not None and not args.checkout_root.is_dir():
        raise FileNotFoundError(args.checkout_root)

    downloaded: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    fetcher = (
        (lambda entry: fetch_local(entry, args.checkout_root))
        if args.checkout_root is not None
        else fetch
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetcher, entry): blob for blob, entry in unique_entries.items()}
        for future in concurrent.futures.as_completed(futures):
            blob = futures[future]
            try:
                entry, content = future.result()
                downloaded[blob] = write_object(args.output, entry, content)
            except Exception as exc:
                errors.append(
                    {
                        "blob_sha": blob,
                        "path": unique_entries[blob]["path"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    records: list[dict[str, Any]] = []
    for candidate in candidates:
        record: dict[str, Any] = {
            key: candidate[key]
            for key in ("candidate_id", "prefix", "total_group_entries")
        }
        for role in ("pdf",):
            entry = candidate[role]
            record[role] = downloaded.get(entry["blob_sha"], {"download_error": True, **entry})
        for role in ("matlab",):
            record[role] = [
                downloaded.get(entry["blob_sha"], {"download_error": True, **entry})
                for entry in candidate[role]
            ]
        for role in ("data", "figures"):
            record[role] = [
                {
                    **entry,
                    "downloaded": False,
                    "download_reason": "metadata-only selection; no API quota spent on auxiliary artifacts",
                }
                for entry in candidate[role]
            ]
        records.append(record)

    by_pdf: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_pdf[str(record["pdf"].get("blob_sha", ""))].append(record["candidate_id"])
    exact_duplicate_pdfs = [
        {"blob_sha": blob, "candidate_ids": ids}
        for blob, ids in sorted(by_pdf.items())
        if blob and len(ids) > 1
    ]

    manifest = {
        "schema_version": 1,
        "source": {
            "repository": REPOSITORY,
            "commit": COMMIT,
            "tree": str(args.tree),
            "tree_entry_count": len(tree["entries"]),
            "tree_truncated": tree["truncated"],
        },
        "selection": {
            "root": SOURCE_ROOT.rstrip("/"),
            "rule": "exactly one PDF and at least one MATLAB file under year/team prefix",
            "candidate_count": len(records),
            "unique_pdf_count": len(by_pdf),
            "downloaded_unique_blob_count": len(downloaded),
            "download_error_count": len(errors),
            "data_cap_per_candidate": 8,
            "figure_cap_per_candidate": 3,
            "auxiliary_artifacts": "metadata_only",
        },
        "exact_duplicate_pdfs": exact_duplicate_pdfs,
        "candidates": records,
        "errors": errors,
    }
    target = args.output / "download_manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "candidate_count": len(records),
                "unique_pdf_count": len(by_pdf),
                "downloaded_unique_blob_count": len(downloaded),
                "download_error_count": len(errors),
                "manifest": str(target),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
