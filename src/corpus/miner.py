from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml


PAPER_CARD_SCHEMA_VERSION = "3.0"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HTTP_RE = re.compile(r"^https://", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    repository: str
    commit: str
    read_only: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SourceSpec":
        source_id = str(value.get("id", "")).strip()
        repository = str(value.get("repository", "")).rstrip("/")
        commit = str(value.get("commit", "")).lower()
        if not source_id or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", source_id):
            raise ValueError("source id must contain only lowercase letters, digits, '_' or '-'")
        if not re.fullmatch(r"https://github\.com/[^/]+/[^/]+", repository):
            raise ValueError(f"unsupported GitHub repository URL: {repository}")
        if not SHA1_RE.fullmatch(commit):
            raise ValueError(f"source {source_id} must use a full 40-character commit")
        if value.get("read_only", True) is not True:
            raise ValueError(f"source {source_id} must be read-only")
        return cls(source_id=source_id, repository=repository, commit=commit)

    @property
    def owner_repo(self) -> str:
        return self.repository.removeprefix("https://github.com/")


def load_source_config(path: Path) -> tuple[dict[str, Any], list[SourceSpec]]:
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if int(config.get("schema_version", 0)) != 1:
        raise ValueError("config/corpus_sources.yaml must use schema_version 1")
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("corpus source config has no repositories")
    specs = [SourceSpec.from_mapping(item) for item in repositories]
    if len({item.source_id for item in specs}) != len(specs):
        raise ValueError("corpus source ids must be unique")
    return config, specs


def _github_tree_url(spec: SourceSpec) -> str:
    owner_repo = urllib.parse.quote(spec.owner_repo, safe="/")
    return f"https://api.github.com/repos/{owner_repo}/git/trees/{spec.commit}?recursive=1"


def _read_url(url: str, *, accept: str = "application/vnd.github+json") -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": "math-modeling-corpus-miner/1"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").lstrip("/")
    parts = normalized.split("/")
    if not normalized or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe repository path: {value!r}")
    return normalized


def _normalize_tree_entries(tree_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    if tree_payload.get("truncated") is True:
        raise ValueError("GitHub returned a truncated recursive tree; refusing an incomplete manifest")
    tree = tree_payload.get("tree")
    if not isinstance(tree, list):
        raise ValueError("Git tree payload has no tree array")
    normalized: list[dict[str, Any]] = []
    for raw in tree:
        if raw.get("type") != "blob":
            continue
        path = _safe_relative_path(str(raw.get("path", "")))
        blob_sha = str(raw.get("sha", "")).lower()
        if not SHA1_RE.fullmatch(blob_sha):
            raise ValueError(f"invalid blob SHA for {path}")
        size = int(raw.get("size", 0))
        if size < 0:
            raise ValueError(f"negative blob size for {path}")
        normalized.append(
            {
                "path": path,
                "blob_sha": blob_sha,
                "bytes": size,
                "extension": Path(path).suffix.lower(),
            }
        )
    return sorted(normalized, key=lambda item: item["path"].casefold())


def _content_addressed_path(root: Path, digest: str) -> Path:
    return root / "objects" / "sha256" / digest[:2] / digest


def _cache_verified_blob(
    spec: SourceSpec,
    entry: Mapping[str, Any],
    content: bytes,
    output_root: Path,
) -> dict[str, Any]:
    expected_size = int(entry["bytes"])
    if len(content) != expected_size:
        raise ValueError(f"blob size mismatch for {entry['path']}: {len(content)} != {expected_size}")
    observed_git_sha = git_blob_sha1(content)
    if observed_git_sha != entry["blob_sha"]:
        raise ValueError(f"Git blob SHA mismatch for {entry['path']}")
    digest = sha256_bytes(content)
    target = _content_addressed_path(output_root, digest)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return {
        "path": entry["path"],
        "blob_sha": entry["blob_sha"],
        "sha256": digest,
        "bytes": len(content),
        "object": target.relative_to(output_root).as_posix(),
        "repository": spec.repository,
        "commit": spec.commit,
    }


def sync_git_tree(
    spec: SourceSpec,
    output_root: Path,
    *,
    tree_payload: Mapping[str, Any] | None = None,
    fetch_bytes: Callable[[str], bytes] | None = None,
    download_small: bool = False,
    max_blob_bytes: int = 1_000_000,
    allowed_extensions: Iterable[str] = (".m", ".tex", ".md", ".txt", ".csv", ".json", ".yaml", ".yml"),
) -> dict[str, Any]:
    """Persist a reproducible read-only Git tree manifest.

    By default this only fetches Git metadata. ``download_small`` is an explicit opt-in,
    bounded by both an extension allow-list and ``max_blob_bytes``. Downloaded objects
    are verified against Git's blob SHA-1 before being stored by SHA-256.
    """

    if max_blob_bytes < 0:
        raise ValueError("max_blob_bytes must be non-negative")
    fetch = fetch_bytes or _read_url
    if tree_payload is None:
        tree_payload = json.loads(fetch(_github_tree_url(spec)).decode("utf-8"))
    entries = _normalize_tree_entries(tree_payload)
    extensions = {item.lower() if item.startswith(".") else f".{item.lower()}" for item in allowed_extensions}
    source_dir = output_root / "sources" / spec.source_id / spec.commit
    tree_path = source_dir / "git_tree.json"
    manifest_path = source_dir / "manifest.json"
    tree_document = {
        "schema_version": 1,
        "source_id": spec.source_id,
        "repository": spec.repository,
        "commit": spec.commit,
        "tree_sha": tree_payload.get("sha"),
        "truncated": False,
        "entries": entries,
    }
    _write_json(tree_path, tree_document)

    cached: list[dict[str, Any]] = []
    skipped_large = 0
    skipped_extension = 0
    if download_small:
        for entry in entries:
            if entry["extension"] not in extensions:
                skipped_extension += 1
                continue
            if entry["bytes"] > max_blob_bytes:
                skipped_large += 1
                continue
            encoded_path = urllib.parse.quote(entry["path"], safe="/")
            raw_url = f"https://raw.githubusercontent.com/{spec.owner_repo}/{spec.commit}/{encoded_path}"
            cached.append(_cache_verified_blob(spec, entry, fetch(raw_url), output_root))

    counts = Counter(entry["extension"] or "<none>" for entry in entries)
    manifest = {
        "schema_version": 1,
        "source_id": spec.source_id,
        "repository": spec.repository,
        "commit": spec.commit,
        "read_only": True,
        "tree_file": tree_path.relative_to(output_root).as_posix(),
        "entry_count": len(entries),
        "total_bytes": sum(entry["bytes"] for entry in entries),
        "extension_counts": dict(sorted(counts.items())),
        "download_policy": "small_allowlisted" if download_small else "metadata_only",
        "download_limit_bytes": max_blob_bytes,
        "cached": cached,
        "cached_count": len(cached),
        "skipped_large": skipped_large,
        "skipped_extension": skipped_extension,
    }
    _write_json(manifest_path, manifest)
    return manifest


def _same_identity(identity: Mapping[str, Any], evidence: Mapping[str, Any]) -> bool:
    required = ("contest", "year", "problem")
    if not all(identity.get(key) not in (None, "") and evidence.get(key) not in (None, "") for key in required):
        return False
    if any(str(identity[key]).casefold() != str(evidence[key]).casefold() for key in required):
        return False
    team_identity = str(identity.get("team_id", "")).strip()
    team_evidence = str(evidence.get("team_id", "")).strip()
    title_identity = str(identity.get("title", "")).strip().casefold()
    title_evidence = str(evidence.get("title", "")).strip().casefold()
    return bool(team_identity and team_evidence and team_identity == team_evidence) or bool(
        title_identity and title_evidence and title_identity == title_evidence
    )


def classify_authenticity(record: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a source using explicit evidence; filenames are intentionally ignored."""

    source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
    identity = record.get("identity") if isinstance(record.get("identity"), Mapping) else {}
    award = record.get("award_evidence") if isinstance(record.get("award_evidence"), Mapping) else {}
    accessible = source.get("accessible") is True
    source_url = str(source.get("url", ""))
    official_url = str(award.get("official_url", ""))
    publisher = str(source.get("publisher", "")).casefold()
    fulltext = source.get("fulltext") is True
    official_award = award.get("verified") is True and HTTP_RE.match(official_url) is not None
    identity_aligned = _same_identity(identity, award) if official_award else False
    checks = {
        "source_accessible": accessible,
        "source_url_https": HTTP_RE.match(source_url) is not None,
        "official_publisher": publisher == "official",
        "mirror_publisher": publisher == "mirror",
        "fulltext_available": fulltext,
        "official_award_verified": official_award,
        "identity_aligned": identity_aligned,
    }
    reasons: list[str] = []
    if accessible and checks["source_url_https"] and publisher == "official" and (fulltext or official_award):
        level = "A"
        reasons.append("official source or official result is directly verifiable")
    elif (
        accessible
        and checks["source_url_https"]
        and publisher == "mirror"
        and fulltext
        and official_award
        and identity_aligned
    ):
        level = "B"
        reasons.append("mirror full text is aligned to a structured official award record")
    elif checks["source_url_https"] and (identity or source):
        level = "C"
        reasons.append("metadata is indexable but award/full-text evidence is insufficient")
    else:
        level = "D"
        reasons.append("source is inaccessible or cannot be verified")
    if record.get("filename_claim"):
        reasons.append("filename claims were ignored")
    return {"level": level, "checks": checks, "reasons": reasons}


def _require_list(record: Mapping[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def _has_page_locator(item: Any) -> bool:
    return isinstance(item, Mapping) and (
        isinstance(item.get("page"), int) or bool(str(item.get("locator", "")).strip())
    )


def content_deep_read_errors(card: Mapping[str, Any]) -> list[str]:
    """Validate full-text content evidence independently from award authenticity."""

    errors: list[str] = []
    authenticity = card.get("authenticity") if isinstance(card.get("authenticity"), Mapping) else {}
    if authenticity.get("level") not in {"A", "B", "C"}:
        errors.append("evidence_deep_read requires accessible A, B, or C source evidence")
    source = card.get("source") if isinstance(card.get("source"), Mapping) else {}
    if source.get("accessible") is not True or source.get("fulltext") is not True:
        errors.append("evidence_deep_read requires accessible fixed full text")

    pdf = card.get("pdf") if isinstance(card.get("pdf"), Mapping) else {}
    digest = str(pdf.get("sha256", ""))
    if not SHA256_RE.fullmatch(digest):
        errors.append("evidence_deep_read requires pdf.sha256")
    pages = pdf.get("pages")
    if not isinstance(pages, int) or pages < 1:
        errors.append("evidence_deep_read requires a positive pdf.pages")

    required_lists = (
        "page_evidence",
        "abstract_structure",
        "model_chain",
        "validation_chain",
        "figures",
        "transferable_rules",
        "risks",
    )
    values: dict[str, list[Any]] = {}
    for key in required_lists:
        value = card.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"evidence_deep_read requires {key}")
            values[key] = []
        else:
            values[key] = value

    for index, item in enumerate(values["page_evidence"]):
        if not isinstance(item, Mapping):
            continue
        if not str(item.get("locator", "")).strip():
            errors.append(f"page_evidence[{index}] requires a visible-page locator")
        if not str(item.get("render", "")).strip():
            errors.append(f"page_evidence[{index}] requires a rendered-page path")
        if item.get("derivation") not in {"visual", "text", "ocr", "mixed"}:
            errors.append(f"page_evidence[{index}] requires a derivation method")

    for key in ("abstract_structure", "model_chain", "validation_chain"):
        for index, item in enumerate(values[key]):
            if not _has_page_locator(item):
                errors.append(f"{key}[{index}] requires page or locator evidence")

    for index, item in enumerate(values["figures"]):
        if not isinstance(item, Mapping):
            errors.append(f"figures[{index}] must be an object")
            continue
        if not isinstance(item.get("page"), int) or item.get("page", 0) < 1:
            errors.append(f"figures[{index}] requires a positive page")
        if not str(item.get("role", "")).strip():
            errors.append(f"figures[{index}] requires a communication role")
        if not str(item.get("chart_type") or item.get("type") or "").strip():
            errors.append(f"figures[{index}] requires a chart type")
        if not str(item.get("lesson", "")).strip():
            errors.append(f"figures[{index}] requires a transferable lesson")
    return errors


def is_award_verified_deep_read(card: Mapping[str, Any]) -> bool:
    classification = classify_authenticity(card)
    checks = classification["checks"]
    return (
        card.get("review_status") == "evidence_deep_read"
        and not content_deep_read_errors(card)
        and classification["level"] in {"A", "B"}
        and checks["official_award_verified"]
        and checks["identity_aligned"]
    )


def validate_paper_card(card: Mapping[str, Any], *, require_deep_read: bool = False) -> list[str]:
    errors: list[str] = []
    schema_version = str(card.get("schema_version", ""))
    if schema_version != PAPER_CARD_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PAPER_CARD_SCHEMA_VERSION}")
    if not str(card.get("paper_id", "")).strip():
        errors.append("paper_id is required")
    identity = card.get("identity")
    if not isinstance(identity, Mapping):
        errors.append("identity must be an object")
    source = card.get("source")
    if not isinstance(source, Mapping):
        errors.append("source must be an object")
    elif not HTTP_RE.match(str(source.get("url", ""))):
        errors.append("source.url must be HTTPS")
    classification = classify_authenticity(card)
    authenticity = card.get("authenticity") if isinstance(card.get("authenticity"), Mapping) else {}
    if authenticity.get("level") != classification["level"]:
        errors.append("authenticity level does not match structured evidence")
    digest = str(card.get("pdf", {}).get("sha256", "")) if isinstance(card.get("pdf"), Mapping) else ""
    if digest and not SHA256_RE.fullmatch(digest):
        errors.append("pdf.sha256 must be a 64-character lowercase SHA-256")
    list_fields = (
        "page_evidence",
        "abstract_structure",
        "model_chain",
        "validation_chain",
        "figures",
        "code_links",
        "transferable_rules",
        "risks",
    )
    lists = {key: _require_list(card, key, errors) for key in list_fields}
    for index, item in enumerate(lists["page_evidence"]):
        if not isinstance(item, Mapping) or not isinstance(item.get("page"), int) or not str(item.get("observation", "")).strip():
            errors.append(f"page_evidence[{index}] needs integer page and observation")
    deep_read = card.get("review_status") == "evidence_deep_read"
    if require_deep_read and not deep_read:
        errors.append("require_deep_read requires review_status evidence_deep_read")
    if deep_read or require_deep_read:
        errors.extend(content_deep_read_errors(card))
    return errors


def build_paper_card(record: Mapping[str, Any], *, require_deep_read: bool = False) -> dict[str, Any]:
    authenticity = classify_authenticity(record)
    source = dict(record.get("source", {}))
    if not source.get("access"):
        if source.get("accessible") is True and source.get("fulltext") is True:
            source["access"] = "public_full_text" if source.get("publisher") == "official" else "mirror_full_text"
        elif source.get("accessible") is True:
            source["access"] = "index_only_metadata"
        else:
            source["access"] = "unavailable"
    award_evidence = dict(record.get("award_evidence", {}))
    for key, default in (
        ("verified", False),
        ("official_url", ""),
        ("contest", ""),
        ("year", None),
        ("problem", ""),
        ("team_id", ""),
        ("title", ""),
        ("award", ""),
    ):
        award_evidence.setdefault(key, default)
    pdf = dict(record.get("pdf", {}))
    pdf.setdefault("sha256", "")
    pdf.setdefault("pages", None)
    pdf.setdefault("local_path", "")
    card = {
        "schema_version": PAPER_CARD_SCHEMA_VERSION,
        "paper_id": record.get("paper_id"),
        "identity": dict(record.get("identity", {})),
        "source": source,
        "award_evidence": award_evidence,
        "authenticity": authenticity,
        "pdf": pdf,
        "review_status": record.get("review_status", "indexed"),
        "page_evidence": list(record.get("page_evidence", [])),
        "abstract_structure": list(record.get("abstract_structure", [])),
        "model_chain": list(record.get("model_chain", [])),
        "validation_chain": list(record.get("validation_chain", [])),
        "figures": list(record.get("figures", [])),
        "code_links": list(record.get("code_links", [])),
        "transferable_rules": list(record.get("transferable_rules", [])),
        "risks": list(record.get("risks", [])),
        "provenance": dict(record.get("provenance", {})),
    }
    errors = validate_paper_card(card, require_deep_read=require_deep_read)
    if errors:
        raise ValueError("invalid paper_card v3: " + "; ".join(errors))
    return card


def _parse_phash(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).lower().removeprefix("0x")
    if not re.fullmatch(r"[0-9a-f]{8,64}", text):
        return None
    return int(text, 16)


def phash_distance(left: Any, right: Any) -> int | None:
    lhs = _parse_phash(left)
    rhs = _parse_phash(right)
    if lhs is None or rhs is None:
        return None
    return (lhs ^ rhs).bit_count()


def _text_features(value: str, n: int = 3) -> Counter[str]:
    normalized = re.sub(r"\s+", "", value).casefold()
    normalized = re.sub(r"(?:watermark|水印|仅供学习|www\.[a-z0-9.-]+)", "", normalized)
    if not normalized:
        return Counter()
    if len(normalized) < n:
        return Counter({normalized: 1})
    return Counter(normalized[index : index + n] for index in range(len(normalized) - n + 1))


def text_similarity(left: str, right: str) -> float:
    lhs = _text_features(left)
    rhs = _text_features(right)
    if not lhs or not rhs:
        return 0.0
    overlap = set(lhs) & set(rhs)
    numerator = sum(lhs[token] * rhs[token] for token in overlap)
    lhs_norm = math.sqrt(sum(value * value for value in lhs.values()))
    rhs_norm = math.sqrt(sum(value * value for value in rhs.values()))
    return numerator / (lhs_norm * rhs_norm)


def deduplicate_records(
    records: Sequence[Mapping[str, Any]],
    *,
    phash_threshold: int = 8,
    text_threshold: float = 0.92,
) -> dict[str, Any]:
    ids = [str(record.get("id", "")).strip() for record in records]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("deduplication records require unique non-empty ids")
    exact_groups: dict[str, list[str]] = {}
    for record, record_id in zip(records, ids):
        digest = str(record.get("sha256", "")).lower()
        if SHA256_RE.fullmatch(digest):
            exact_groups.setdefault(digest, []).append(record_id)
    exact = [
        {"canonical_id": group[0], "duplicate_ids": group[1:], "sha256": digest}
        for digest, group in sorted(exact_groups.items())
        if len(group) > 1
    ]
    canonical_by_id = {record_id: record_id for record_id in ids}
    for group in exact:
        for duplicate in group["duplicate_ids"]:
            canonical_by_id[duplicate] = group["canonical_id"]
    probable: list[dict[str, Any]] = []
    for left_index, left in enumerate(records):
        for right_index in range(left_index + 1, len(records)):
            right = records[right_index]
            left_digest = str(left.get("sha256", "")).lower()
            right_digest = str(right.get("sha256", "")).lower()
            if SHA256_RE.fullmatch(left_digest) and left_digest == right_digest:
                continue
            distance = phash_distance(left.get("first_page_phash"), right.get("first_page_phash"))
            similarity = text_similarity(str(left.get("text", "")), str(right.get("text", "")))
            methods: list[str] = []
            if distance is not None and distance <= phash_threshold:
                methods.append("first_page_phash")
            if similarity >= text_threshold:
                methods.append("text_similarity")
            if methods:
                probable.append(
                    {
                        "left_id": ids[left_index],
                        "right_id": ids[right_index],
                        "methods": methods,
                        "phash_distance": distance,
                        "text_similarity": round(similarity, 6),
                        "action": "review_keep_separate",
                    }
                )
    return {
        "schema_version": 1,
        "exact_groups": exact,
        "canonical_by_id": canonical_by_id,
        "unique_after_exact_merge": len(set(canonical_by_id.values())),
        "probable_duplicates": probable,
        "policy": {
            "exact": "merge_by_sha256",
            "perceptual_or_text": "flag_for_review_without_automatic_merge",
            "phash_threshold": phash_threshold,
            "text_threshold": text_threshold,
        },
    }


_MATLAB_RISK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "absolute_path": (
        re.compile(r"(?i)(?:['\"])[a-z]:[\\/]"),
        re.compile(r"(?i)(?:['\"])(?:/home/|/users/|\\\\)"),
    ),
    "delete_or_overwrite": (
        re.compile(r"(?i)\b(?:delete|rmdir)\s*\("),
        re.compile(r"(?im)^\s*!\s*(?:del|erase|rm)\b"),
    ),
    "system_call": (
        re.compile(r"(?i)\b(?:system|dos|unix)\s*\("),
        re.compile(r"(?m)^\s*!\s*\S+"),
    ),
    "network": (
        re.compile(r"(?i)\b(?:webread|webwrite|urlread|urlwrite|tcpclient|udpport|ftp|matlab\.net\.)\b"),
        re.compile(r"(?i)https?://"),
    ),
    "interactive_gui": (
        re.compile(r"(?i)\b(?:uifigure|uidropdown|uibutton|uitable|inputdlg|questdlg|msgbox|waitbar|uigetfile|uiputfile)\s*\("),
    ),
    "dynamic_execution": (
        re.compile(r"(?i)\b(?:eval|evalin|assignin)\s*\("),
    ),
}

_TOOLBOX_FUNCTIONS: dict[str, set[str]] = {
    "Optimization Toolbox": {"linprog", "intlinprog", "quadprog", "fmincon", "fminunc", "lsqnonlin", "optimproblem", "optimvar"},
    "Global Optimization Toolbox": {"ga", "particleswarm", "simulannealbnd", "patternsearch", "gamultiobj"},
    "Statistics and Machine Learning Toolbox": {"fitlm", "fitnlm", "fitcsvm", "fitctree", "kmeans", "pca", "regress", "anova1", "bootstrp"},
    "Image Processing Toolbox": {"imbinarize", "imfilter", "regionprops", "bwlabel", "imresize", "imadjust"},
    "Signal Processing Toolbox": {"butter", "filtfilt", "periodogram", "spectrogram", "findpeaks"},
    "Curve Fitting Toolbox": {"fit", "cfit", "sfit", "preparecurveData"},
    "Symbolic Math Toolbox": {"syms", "solve", "dsolve", "vpasolve", "matlabfunction"},
    "Mapping Toolbox": {"geoplot", "geoscatter", "geobasemap", "shaperead"},
    "Parallel Computing Toolbox": {"parpool", "parfeval", "gpuarray", "spmd"},
    "Simulink": {"sim", "simulink"},
}


def _matlab_code_without_comments(text: str) -> str:
    lines: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("%{"):
            in_block = True
            continue
        if stripped.startswith("%}"):
            in_block = False
            continue
        if in_block or stripped.startswith("%"):
            continue
        output: list[str] = []
        in_single = False
        in_double = False
        for char in line:
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            if char == "%" and not in_single and not in_double:
                break
            output.append(char)
        lines.append("".join(output))
    return "\n".join(lines)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_matlab_text(text: str, *, path: str = "<memory>") -> dict[str, Any]:
    code = _matlab_code_without_comments(text)
    risks: list[dict[str, Any]] = []
    for category, patterns in _MATLAB_RISK_PATTERNS.items():
        matches: list[dict[str, Any]] = []
        for pattern in patterns:
            for match in pattern.finditer(code):
                matches.append({"line": _line_number(code, match.start()), "match": match.group(0)[:120]})
        if matches:
            unique = {(item["line"], item["match"]): item for item in matches}
            risks.append({"category": category, "occurrences": list(unique.values())})
    lower_code = code.casefold()
    toolboxes: list[dict[str, Any]] = []
    for toolbox, functions in _TOOLBOX_FUNCTIONS.items():
        used = sorted(function for function in functions if re.search(rf"(?i)\b{re.escape(function)}\s*\(?", lower_code))
        if used:
            toolboxes.append({"toolbox": toolbox, "functions": used})
    return {
        "path": path.replace("\\", "/"),
        "sha256": sha256_bytes(text.encode("utf-8")),
        "bytes": len(text.encode("utf-8")),
        "line_count": len(text.splitlines()),
        "risks": risks,
        "toolboxes": toolboxes,
        "execution_policy": "manual_review_required" if risks else "static_scan_clear_not_execution_approval",
    }


def _read_text_best_effort(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def scan_matlab_tree(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    risk_counts: Counter[str] = Counter()
    toolbox_counts: Counter[str] = Counter()
    for path in sorted(root.rglob("*.m"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        text, encoding = _read_text_best_effort(path)
        result = scan_matlab_text(text, path=path.relative_to(root).as_posix())
        result["encoding"] = encoding
        files.append(result)
        risk_counts.update(item["category"] for item in result["risks"])
        toolbox_counts.update(item["toolbox"] for item in result["toolboxes"])
    return {
        "schema_version": 1,
        "root": str(root.resolve()),
        "generated_at_utc": _utc_now(),
        "file_count": len(files),
        "risk_file_counts": dict(sorted(risk_counts.items())),
        "toolbox_file_counts": dict(sorted(toolbox_counts.items())),
        "files": files,
        "execution_policy": "static_index_only_no_bulk_execution",
    }


def index_matlab_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    entries = manifest.get("entries", [])
    files = [
        {"path": item["path"], "blob_sha": item["blob_sha"], "bytes": item["bytes"], "scan_status": "content_not_cached"}
        for item in entries
        if str(item.get("path", "")).lower().endswith(".m")
    ]
    return {
        "schema_version": 1,
        "file_count": len(files),
        "files": files,
        "execution_policy": "metadata_index_only_content_required_for_static_scan",
    }


def _select_sources(specs: Sequence[SourceSpec], selected: str) -> list[SourceSpec]:
    if selected == "all":
        return list(specs)
    matches = [item for item in specs if item.source_id == selected]
    if not matches:
        raise ValueError(f"unknown corpus source: {selected}")
    return matches


def _command_sync(args: argparse.Namespace) -> dict[str, Any]:
    config, specs = load_source_config(args.config)
    selected = _select_sources(specs, args.source)
    manifests: list[dict[str, Any]] = []
    fixture_payload = _read_json(args.tree_fixture) if args.tree_fixture else None
    for spec in selected:
        payload = fixture_payload
        if isinstance(fixture_payload, Mapping) and spec.source_id in fixture_payload:
            payload = fixture_payload[spec.source_id]
        manifests.append(
            sync_git_tree(
                spec,
                args.output,
                tree_payload=payload,
                download_small=args.download_small,
                max_blob_bytes=args.max_blob_bytes or int(config.get("download", {}).get("max_blob_bytes", 1_000_000)),
                allowed_extensions=config.get("download", {}).get("allowed_extensions", []),
            )
        )
    return {"status": "PASS", "manifests": manifests}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-grounded modeling paper corpus pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync", help="sync pinned Git tree metadata")
    sync.add_argument("--config", type=Path, default=Path("config/corpus_sources.yaml"))
    sync.add_argument("--source", default="all")
    sync.add_argument("--output", type=Path, default=Path("corpus/upstream"))
    sync.add_argument("--tree-fixture", type=Path)
    sync.add_argument("--download-small", action="store_true")
    sync.add_argument("--max-blob-bytes", type=int)

    card = subparsers.add_parser("card", help="build and validate a paper_card v3")
    card.add_argument("--input", type=Path, required=True)
    card.add_argument("--output", type=Path, required=True)
    card.add_argument("--require-deep-read", action="store_true")

    dedupe = subparsers.add_parser("dedupe", help="find exact and probable duplicate records")
    dedupe.add_argument("--input", type=Path, required=True)
    dedupe.add_argument("--output", type=Path, required=True)
    dedupe.add_argument("--phash-threshold", type=int, default=8)
    dedupe.add_argument("--text-threshold", type=float, default=0.92)

    scan = subparsers.add_parser("scan-matlab", help="statically scan MATLAB files without executing them")
    scan.add_argument("--root", type=Path)
    scan.add_argument("--tree-manifest", type=Path)
    scan.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            result = _command_sync(args)
        elif args.command == "card":
            result = build_paper_card(_read_json(args.input), require_deep_read=args.require_deep_read)
            _write_json(args.output, result)
        elif args.command == "dedupe":
            payload = _read_json(args.input)
            records = payload.get("records", payload) if isinstance(payload, Mapping) else payload
            result = deduplicate_records(records, phash_threshold=args.phash_threshold, text_threshold=args.text_threshold)
            _write_json(args.output, result)
        elif args.command == "scan-matlab":
            if bool(args.root) == bool(args.tree_manifest):
                raise ValueError("scan-matlab requires exactly one of --root or --tree-manifest")
            if args.root:
                result = scan_matlab_tree(args.root)
            else:
                manifest = _read_json(args.tree_manifest)
                if not manifest.get("entries") and manifest.get("tree_file"):
                    tree_path = Path(manifest["tree_file"])
                    if not tree_path.is_absolute():
                        candidates = [ancestor / tree_path for ancestor in (args.tree_manifest.parent, *args.tree_manifest.parents)]
                        tree_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
                    manifest = _read_json(tree_path)
                result = index_matlab_manifest(manifest)
            _write_json(args.output, result)
        else:
            parser.error("unsupported command")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
