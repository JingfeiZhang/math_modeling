#!/usr/bin/env python3
"""Static, include-aware audit for a mathematics-modeling LaTeX paper."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

PLACEHOLDER_RE = re.compile(r"TODO|TBD|PLACEHOLDER|UNFROZEN CLAIM|待实验结果|待补|XX+", re.I)
ANONYMITY_RE = re.compile(
    r"\\author\s*\{\s*[^}]|\\institute\s*\{\s*[^}]|"
    r"(?:姓名|学号|队号|指导教师|联系方式|邮箱|email|作者单位)\s*[:：]\s*\S+",
    re.I,
)
REF_RE = re.compile(r"\\(?:ref|eqref|pageref|autoref)\s*\{([^{}]+)\}")
CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*\{([^{}]+)\}")
NOCITE_RE = re.compile(r"\\nocite\s*\{([^{}]+)\}")
# Paper-local upper-right numeric citations are semantically equivalent to
# ``\cite`` and must participate in the same bibliography checks.
UP_CITE_RE = re.compile(r"\\UpCite\s*\{([^{}]+)\}")
BIBITEM_RE = re.compile(r"\\bibitem(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}")
INCLUDE_RE = re.compile(r"\\(input|include)\s*\{([^{}]+)\}")
SECTION_RE = re.compile(r"\\section\*?\s*\{([^{}]*)\}")
SUBSECTION_RE = re.compile(r"\\subsection\*?\s*\{([^{}]*)\}")
QUESTION_TITLE_RE = re.compile(r"^\s*问题\s*([一二三四五六七八九十\d]+)")
ARTIFACT_RE = re.compile(r"\\begin\{(figure|table)\*?\}(.*?)\\end\{\1\*?\}", re.S)
AUTHORING_PROMPT_RE = re.compile(
    r"\\(?:WritingContract|TemplatePrompt)\b|AUTHORING_PROMPT|模板提示|表达目标|必写内容|证据要求|禁止内容",
    re.I,
)
INTERNAL_WORKFLOW_RE = re.compile(
    r"(?:Figure\s*Contract|question\s*manifest|frozen\s*claims?|"
    r"冻结主张|证据定位|内部工作流|根\s*Agent|G[0-6]\s*门)",
    re.I,
)

QUESTION_ARGUMENT_KEYS = (
    "objective_interface",
    "model_choice",
    "formulation",
    "algorithm",
    "result",
    "validation",
    "conclusion",
)
QUESTION_ARGUMENT_HEADINGS = (
    "目标与上下游接口",
    "数据特征或机理依据",
    "模型选择与备选方案比较",
    "模型建立",
    "求解算法",
    "核心结果与解释",
    "模型检验",
    "本问结论与适用边界",
)
COMPLETED_STATES = {"complete", "completed", "done", "frozen", "verified", "pass", "passed", "完成", "已完成"}


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def _version_major(value: object) -> int:
    match = re.match(r"\s*(\d+)", str(value or ""))
    return int(match.group(1)) if match else 0


def infer_structure_strict(paper_dir: Path, explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    template = load_yaml(paper_dir / "template.yaml")
    if _version_major(template.get("contract_version")) >= 3:
        return True
    project_root = paper_dir.parent
    for path in project_root.glob("problems/*/questions/Q*/question.yaml"):
        if _version_major(load_yaml(path).get("schema_version")) >= 2:
            return True
    return False


def ordered_citation_keys(text: str) -> list[str]:
    pattern = re.compile(r"\\(?:cite[a-zA-Z*]*|UpCite)\s*\{([^{}]+)\}")
    keys: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and "#" not in key and key != "*" and key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def bibliography_order(combined: str, paper_dir: Path, entry: Path) -> list[str]:
    order = BIBITEM_RE.findall(combined)
    if order:
        return order
    candidates = [entry.with_suffix(".bbl"), paper_dir / "main.bbl"]
    for candidate in candidates:
        if candidate.is_file():
            return BIBITEM_RE.findall(read_tex(candidate))
    return []


def question_number(raw: str) -> int | None:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    values = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return values.get(raw)


def section_records(text: str) -> list[dict]:
    records: list[dict] = []
    matches = list(SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        records.append({"title": plain_text(match.group(1)), "start": match.start(), "end": end, "body": text[match.end():end]})
    return records


def discover_question_manifests(project_root: Path) -> list[tuple[Path, dict]]:
    candidates: list[Path] = []
    state_path = project_root / "state" / "decision_log.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            problem = str(state.get("problem") or "").strip()
        except (json.JSONDecodeError, OSError):
            problem = ""
        if problem:
            candidates = sorted((project_root / "problems" / problem / "questions").glob("Q*/question.yaml"))
    if not candidates:
        candidates = sorted(project_root.glob("problems/*/questions/Q*/question.yaml"))
    manifests: list[tuple[Path, dict]] = []
    for path in candidates:
        data = load_yaml(path)
        if data:
            manifests.append((path, data))
    return manifests


def _nonempty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_nonempty(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_nonempty(item) for item in value)
    return value is not None


def _status_complete(value: object) -> bool:
    if isinstance(value, dict):
        value = value.get("status")
    return str(value or "").strip().lower() in COMPLETED_STATES


def _normal_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _id_is_labeled(identifier: str, labels: set[str]) -> bool:
    target = _normal_id(identifier)
    return bool(target) and any(target == _normal_id(label) or _normal_id(label).endswith(target) for label in labels)


def _question_marker_present(text: str, question_id: str) -> bool:
    match = re.search(r"(\d+)$", question_id.strip().upper())
    if not match:
        return question_id.lower() in text.lower()
    number = int(match.group(1))
    chinese = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}.get(number)
    markers = {f"q{number}", f"问题{number}", f"第{number}问"}
    if chinese:
        markers.update((f"问题{chinese}", f"第{chinese}问"))
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _manifest_tokens(manifest: dict, field: str) -> list[str]:
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), dict) else {}
    values = evidence.get(field) if isinstance(evidence, dict) else []
    return [str(value).strip() for value in values or [] if str(value).strip()]


def strip_comments(text: str) -> str:
    cleaned: list[str] = []
    for line in text.splitlines():
        cut = len(line)
        escaped = False
        for index, char in enumerate(line):
            if char == "%" and not escaped:
                cut = index
                break
            if char == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
        cleaned.append(line[:cut])
    return "\n".join(cleaned)


def read_tex(path: Path) -> str:
    try:
        return strip_comments(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return strip_comments(path.read_text(encoding="gb18030"))


def resolve_include(owner: Path, raw: str) -> Path:
    candidate = (owner.parent / raw.strip()).resolve()
    return candidate if candidate.suffix else candidate.with_suffix(".tex")


def expand_tex(entry: Path) -> tuple[str, dict[str, str], list[dict], list[dict]]:
    texts: dict[str, str] = {}
    missing: list[dict] = []
    cycles: list[dict] = []

    def visit(path: Path, stack: tuple[Path, ...]) -> str:
        path = path.resolve()
        if path in stack:
            cycles.append({"file": str(path), "chain": [str(item) for item in (*stack, path)]})
            return ""
        if not path.is_file():
            missing.append({"file": str(path), "included_from": str(stack[-1]) if stack else None})
            return ""
        text = read_tex(path)
        texts[str(path)] = text
        return INCLUDE_RE.sub(lambda match: visit(resolve_include(path, match.group(2)), (*stack, path)), text)

    return visit(entry, ()), texts, missing, cycles


def add(items: list[dict], code: str, message: str, severity: str, file: str | None = None) -> None:
    item = {"code": code, "message": message, "severity": severity}
    if file:
        item["file"] = file
    items.append(item)


def split_keys(groups: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for group in groups:
        result.update(key.strip() for key in group.split(",") if key.strip() and "#" not in key and key.strip() != "*")
    return result


def resolve_graphic(paper_dir: Path, raw: str) -> Path | None:
    variants: list[Path] = []
    for base in (paper_dir, paper_dir / "figures"):
        candidate = (base / raw).resolve()
        variants.append(candidate)
        if not candidate.suffix:
            variants.extend(candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".svg"))
    return next((path for path in variants if path.is_file()), None)


def plain_text(text: str) -> str:
    text = re.sub(r"\\(?:begin|end)\s*\{[^{}]+\}", " ", text)
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\s*\[[^]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"[$&_#^~\\]", " ", text)
    return re.sub(r"\s+", "", text)


def length_cm(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(cm|mm|in|pt)\s*", value, re.I)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2).lower()
    return number * {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 2.54 / 72.27}[unit]


def geometry_margins(text: str) -> dict[str, float] | None:
    option_sets = re.findall(r"\\usepackage\s*\[([^]]*)\]\s*\{geometry\}", text)
    option_sets.extend(re.findall(r"\\geometry\s*\{([^}]*)\}", text))
    values: dict[str, float] = {}
    for options in option_sets:
        for item in options.split(","):
            if "=" not in item:
                continue
            key, raw = (part.strip().lower() for part in item.split("=", 1))
            parsed = length_cm(raw)
            if parsed is not None:
                values[key] = parsed
    if "margin" in values:
        return {key: values["margin"] for key in ("left", "right", "top", "bottom")}
    aliases = {"left": ("left", "lmargin"), "right": ("right", "rmargin"), "top": ("top", "tmargin"), "bottom": ("bottom", "bmargin")}
    result = {side: next((values[name] for name in names if name in values), None) for side, names in aliases.items()}
    return result if all(value is not None for value in result.values()) else None


def audit_structure(
    combined: str,
    paper_dir: Path,
    labels: set[str],
    errors: list[dict],
    warnings: list[dict],
    metrics: dict,
) -> None:
    records = section_records(combined)
    titles = [record["title"] for record in records]
    metrics["section_titles"] = titles
    if re.search(r"\\tableofcontents\b", combined):
        add(errors, "TOC_FORBIDDEN", "automatic table of contents is forbidden by the CUMCM paper contract", "error")

    def first_index(predicate) -> int | None:
        return next((index for index, record in enumerate(records) if predicate(record["title"])), None)

    expected = [
        ("问题重述", lambda title: "问题重述" in title),
        ("问题分析", lambda title: "问题分析" in title and "问题重述" not in title),
        ("模型假设与符号约定", lambda title: "模型假设" in title and "符号" in title),
        ("数据处理与评价指标", lambda title: "数据处理" in title and "评价指标" in title),
    ]
    positions: list[tuple[str, int]] = []
    for name, predicate in expected:
        position = first_index(predicate)
        if position is None:
            add(errors, "SECTION_MISSING", f"required front-body section is missing: {name}", "error")
        else:
            positions.append((name, position))
    if positions and [position for _, position in positions] != sorted(position for _, position in positions):
        add(errors, "SECTION_ORDER", "front-body sections are not in the required order", "error")

    question_records: list[tuple[int, dict]] = []
    for record in records:
        match = QUESTION_TITLE_RE.match(record["title"])
        if match:
            number = question_number(match.group(1))
            if number is not None:
                question_records.append((number, record))
    question_numbers = [number for number, _ in question_records]
    metrics["question_sections"] = question_numbers
    if not question_records:
        add(errors, "QUESTION_SECTIONS_MISSING", "no question model sections were found", "error")
    elif question_numbers != list(range(1, len(question_numbers) + 1)):
        add(errors, "QUESTION_SEQUENCE", f"question sections are not consecutive from Q1: {question_numbers}", "error")

    evaluation_index = first_index(lambda title: "模型评价" in title and "推广" in title)
    if evaluation_index is None:
        add(errors, "SECTION_MISSING", "required closing section is missing: 模型评价与推广", "error")
    elif question_records:
        final_question_index = records.index(question_records[-1][1])
        if evaluation_index <= final_question_index:
            add(errors, "SECTION_ORDER", "模型评价与推广 must follow all question sections", "error")
    data_index = first_index(lambda title: "数据处理" in title and "评价指标" in title)
    if data_index is not None and question_records and records.index(question_records[0][1]) <= data_index:
        add(errors, "SECTION_ORDER", "question sections must follow 数据处理与评价指标", "error")

    reference_position = combined.find("\\begin{thebibliography}")
    reference_section = next((record for record in records if "参考文献" in record["title"]), None)
    if reference_position < 0 and reference_section:
        reference_position = reference_section["start"]
    appendix_positions = [position for position in (combined.find("\\appendix"),) if position >= 0]
    appendix_section = next((record for record in records if record["title"].startswith("附录")), None)
    if appendix_section:
        appendix_positions.append(appendix_section["start"])
    appendix_position = min(appendix_positions) if appendix_positions else -1
    if reference_position < 0:
        add(errors, "REFERENCES_SECTION_MISSING", "reference section is missing", "error")
    if appendix_position < 0:
        add(errors, "APPENDIX_MISSING", "appendix is missing", "error")
    if reference_position >= 0 and appendix_position >= 0 and appendix_position <= reference_position:
        add(errors, "SECTION_ORDER", "appendix must follow the references", "error")
    if appendix_position >= 0:
        appendix_text = combined[appendix_position:]
        if re.search(r"\\(?:section|subsection|subsubsection)\*?\s*\{[^{}]*符号", appendix_text) or re.search(
            r"\\caption\s*\{[^{}]*符号表", appendix_text
        ):
            add(errors, "APPENDIX_SYMBOL_TABLE", "the appendix repeats a symbol table that must remain in the front body", "error")
    body_end = reference_position if reference_position >= 0 else (appendix_position if appendix_position >= 0 else len(combined))
    body_text = combined[:body_end]
    if AUTHORING_PROMPT_RE.search(combined):
        add(errors, "AUTHORING_PROMPT", "authoring-contract prompt text remains in the formal manuscript", "error")
    if INTERNAL_WORKFLOW_RE.search(body_text):
        add(errors, "INTERNAL_WORKFLOW_TEXT", "internal workflow terminology appears in the contest-paper body", "error")

    manifests = discover_question_manifests(paper_dir.parent)
    metrics["question_manifests"] = len(manifests)
    if not manifests:
        add(errors, "QUESTION_MANIFESTS_MISSING", "no question manifests are available for the paper evidence handoff", "error")
    elif len(manifests) != len(question_records):
        add(errors, "QUESTION_COUNT_MISMATCH", f"paper has {len(question_records)} question section(s) but {len(manifests)} manifest(s)", "error")

    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", combined, re.S)
    abstract_text = plain_text(abstract_match.group(1)) if abstract_match else ""
    abstract_coverage: dict[str, dict[str, bool]] = {}
    question_by_number = {number: record for number, record in question_records}
    for path, manifest in manifests:
        qid = str(manifest.get("question_id") or path.parent.name).strip().upper()
        match = re.search(r"(\d+)$", qid)
        number = int(match.group(1)) if match else None
        if _version_major(manifest.get("schema_version")) < 2:
            add(errors, "QUESTION_SCHEMA_V1", f"{qid or path.parent.name} must use question manifest schema v2 at G5", "error", str(path))
            continue
        model_selection = manifest.get("model_selection") if isinstance(manifest.get("model_selection"), dict) else {}
        primary = str(model_selection.get("primary") or "").strip()
        result_ids = _manifest_tokens(manifest, "result_claim_ids")
        validation_ids = _manifest_tokens(manifest, "validation_claim_ids")
        coverage = {
            "question_marker": _question_marker_present(abstract_text, qid),
            "primary_model": bool(primary) and plain_text(primary) in abstract_text,
            "result_claim": bool(result_ids) and any(plain_text(value) in abstract_text for value in result_ids),
            "validation_claim": bool(validation_ids) and any(plain_text(value) in abstract_text for value in validation_ids),
        }
        abstract_coverage[qid] = coverage
        missing_coverage = [name for name, passed in coverage.items() if not passed]
        if missing_coverage:
            add(
                errors,
                "ABSTRACT_QUESTION_COVERAGE",
                f"{qid} abstract coverage is incomplete: {', '.join(missing_coverage)}",
                "error",
                str(path),
            )
        record = question_by_number.get(number) if number is not None else None
        if record is None:
            add(errors, "QUESTION_SECTION_MISSING", f"manifest {qid} has no matching paper section", "error", str(path))
            continue
        subsection_titles = [plain_text(value) for value in SUBSECTION_RE.findall(record["body"])]
        for heading in QUESTION_ARGUMENT_HEADINGS:
            if not any(heading in title for title in subsection_titles):
                add(errors, "ARGUMENT_SECTION_MISSING", f"{qid} is missing argument section: {heading}", "error", str(path))
        if len(plain_text(record["body"])) < 180:
            add(errors, "QUESTION_SECTION_EMPTY", f"{qid} contains too little substantive text", "error", str(path))

        paper = manifest.get("paper") if isinstance(manifest.get("paper"), dict) else {}
        contract = paper.get("argument_contract") if isinstance(paper.get("argument_contract"), dict) else {}
        for key in QUESTION_ARGUMENT_KEYS:
            if not _status_complete(contract.get(key)):
                add(errors, "ARGUMENT_CONTRACT_INCOMPLETE", f"{qid} argument contract is not complete: {key}", "error", str(path))
        evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), dict) else {}
        required_evidence = {
            "result_claim_ids": "result claim",
            "validation_claim_ids": "validation claim",
            "boundary_claim_ids": "boundary claim",
        }
        for field, label in required_evidence.items():
            if not _nonempty(evidence.get(field)):
                add(errors, "QUESTION_EVIDENCE_MISSING", f"{qid} has no {label} binding ({field})", "error", str(path))
        if not _nonempty(model_selection.get("baseline")):
            add(errors, "QUESTION_BASELINE_MISSING", f"{qid} has no same-output baseline binding", "error", str(path))
        artifact_ids = [str(value) for field in ("figure_ids", "table_ids") for value in (paper.get(field) or [])]
        if not artifact_ids:
            add(errors, "QUESTION_ARTIFACT_MISSING", f"{qid} has no result figure or table binding", "error", str(path))
        for identifier in artifact_ids:
            if not _id_is_labeled(identifier, labels):
                add(errors, "QUESTION_ARTIFACT_UNBOUND", f"{qid} artifact id is not labeled in the manuscript: {identifier}", "error", str(path))
        if not _nonempty(paper.get("code_refs")):
            add(errors, "QUESTION_CODE_REF_MISSING", f"{qid} has no formal code reference", "error", str(path))
        if not _nonempty(paper.get("downstream_interfaces")):
            add(errors, "QUESTION_INTERFACE_MISSING", f"{qid} has no downstream or final-output interface", "error", str(path))
        claim_ids = [str(value) for field in required_evidence for value in (evidence.get(field) or [])]
        if claim_ids and not any(identifier in record["body"] for identifier in claim_ids):
            add(errors, "QUESTION_CLAIM_NOT_USED", f"{qid} section does not reference any of its frozen claim ids", "error", str(path))
    metrics["abstract_question_coverage"] = abstract_coverage


def audit_artifact_flow(combined: str, errors: list[dict], warnings: list[dict], strict: bool) -> None:
    references: dict[str, list[int]] = {}
    for match in REF_RE.finditer(combined):
        references.setdefault(match.group(1), []).append(match.start())
    artifacts = list(ARTIFACT_RE.finditer(combined))
    section_starts = [match.start() for match in SECTION_RE.finditer(combined)]
    boundaries = sorted(section_starts + [match.start() for match in artifacts] + [match.end() for match in artifacts])
    for match in artifacts:
        kind, block = match.group(1), match.group(2)
        artifact_labels = LABEL_RE.findall(block)
        if not artifact_labels:
            add(errors if strict else warnings, "ARTIFACT_LABEL_MISSING", f"{kind} environment has no label", "error" if strict else "warning")
            continue
        for label in artifact_labels:
            external_refs = [position for position in references.get(label, []) if not (match.start() <= position <= match.end())]
            if not external_refs:
                add(errors if strict else warnings, "ARTIFACT_UNREFERENCED", f"artifact is not referenced in the body: {label}", "error" if strict else "warning")
                continue
            first_ref = min(external_refs)
            if first_ref > match.start():
                add(errors if strict else warnings, "ARTIFACT_BEFORE_REFERENCE", f"artifact appears before its first body reference: {label}", "error" if strict else "warning")
            if abs(match.start() - first_ref) > 2500:
                add(warnings, "ARTIFACT_REFERENCE_FAR", f"first reference is far from artifact: {label}", "warning")
        previous = max((value for value in boundaries if value < match.start()), default=0)
        following = min((value for value in boundaries if value > match.end()), default=len(combined))
        context = combined[max(previous, match.start() - 1400):match.start()] + combined[match.end():min(following, match.end() + 1400)]
        context = REF_RE.sub("", context)
        if len(plain_text(context)) < 35:
            add(errors if strict else warnings, "ARTIFACT_EXPLANATION_MISSING", f"{kind} lacks nearby explanatory prose", "error" if strict else "warning")


def audit_latex_log(log_path: Path | None, errors: list[dict], warnings: list[dict], metrics: dict, strict: bool) -> None:
    metrics["latex_log"] = str(log_path) if log_path else None
    if log_path is None or not log_path.is_file():
        if strict:
            add(warnings, "LATEX_LOG_NOT_FOUND", "LaTeX log was not found; compiled-layout diagnostics were not checked", "warning")
        return
    text = log_path.read_text(encoding="utf-8", errors="replace")
    checks = (
        ("OVERFULL_BOX", r"Overfull \\[hv]box", "LaTeX log contains an overfull box"),
        ("LOG_UNDEFINED_REFERENCE", r"(?:Reference `[^']+' on page \d+ undefined|There were undefined references)", "LaTeX log contains undefined references"),
        ("LOG_UNDEFINED_CITATION", r"(?:Citation `[^']+' on page \d+ undefined|There were undefined citations|Package natbib Warning: Citation)", "LaTeX log contains undefined citations"),
        ("LOG_DUPLICATE_LABEL", r"(?:Label `[^']+' multiply defined|multiply-defined labels)", "LaTeX log contains multiply defined labels"),
    )
    for code, pattern, message in checks:
        count = len(re.findall(pattern, text, re.I))
        if count:
            add(errors, code, f"{message} ({count} occurrence(s))", "error", str(log_path))


def pdf_metrics(pdf_path: Path) -> tuple[int | None, str | None]:
    if not pdf_path.is_file():
        return None, "PDF file not found"
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages), None
    except Exception:
        pass
    try:
        result = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True)
        match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
        if match:
            return int(match.group(1)), None
    except Exception as exc:
        return None, f"could not read PDF page count ({exc})"
    return None, "could not read PDF page count"


def audit(args: argparse.Namespace) -> dict:
    page_limit_policy = "required"
    hard_body_max_pages = args.max_pages
    hard_total_max_pages = args.max_pages + 1
    if args.contest_config:
        contest = load_yaml(Path(args.contest_config).resolve())
        format_cfg = contest.get("format", {})
        args.max_pages = int(format_cfg.get("paper_body_max_pages", args.max_pages))
        page_limit_policy = str(format_cfg.get("paper_body_limit_policy", "required")).strip().lower()
        hard_body_max_pages = int(format_cfg.get("paper_body_hard_max_pages", args.max_pages))
        hard_total_max_pages = int(format_cfg.get("paper_total_hard_max_pages", hard_body_max_pages + 1))
        args.max_pdf_mb = float(format_cfg.get("paper_max_mb", args.max_pdf_mb))
        args.min_margin_cm = float(format_cfg.get("min_margin_cm", args.min_margin_cm))
        args.require_anonymous = bool(format_cfg.get("require_anonymous", args.require_anonymous))
    paper_dir = Path(args.paper_dir).resolve()
    structure_strict = infer_structure_strict(paper_dir, getattr(args, "structure_strict", None))
    errors: list[dict] = []
    warnings: list[dict] = []
    info: list[dict] = []
    if not paper_dir.is_dir():
        add(errors, "PAPER_DIR_MISSING", f"paper directory does not exist: {paper_dir}", "error")
        return {"schema_version": 2, "passed": False, "errors": errors, "warnings": warnings, "info": info, "metrics": {}}

    entry = paper_dir / "main.tex"
    if not entry.is_file():
        candidates = sorted(paper_dir.glob("*.tex"))
        entry = candidates[0] if candidates else entry
    combined, files, missing, cycles = expand_tex(entry)
    for item in missing:
        add(errors, "MISSING_INCLUDE", f"included TeX file does not exist: {item['file']}", "error", item.get("included_from"))
    for item in cycles:
        add(errors, "INCLUDE_CYCLE", "cyclic TeX include: " + " -> ".join(item["chain"]), "error", item["file"])
    all_tex = {str(path.resolve()) for path in paper_dir.rglob("*.tex")}
    orphaned = sorted(all_tex - set(files))
    if orphaned:
        add(warnings, "ORPHAN_TEX", f"{len(orphaned)} TeX file(s) are not reachable from {entry.name}", "warning")

    cite_groups = CITE_RE.findall(combined) + UP_CITE_RE.findall(combined) + NOCITE_RE.findall(combined)
    metrics = {
        "entrypoint": str(entry), "tex_files": len(files), "orphan_tex_files": len(orphaned),
        "labels": len(LABEL_RE.findall(combined)), "refs": len(REF_RE.findall(combined)),
        "citations": len(cite_groups), "graphics": len(GRAPHICS_RE.findall(combined)),
        "sections": len(re.findall(r"\\section\*?\s*\{", combined)),
        "tables": len(re.findall(r"\\begin\{table\*?\}", combined)),
        "figures": len(re.findall(r"\\begin\{figure\*?\}", combined)),
        "structure_strict": structure_strict,
    }
    if not files:
        add(errors, "NO_TEX", "no readable TeX entrypoint found", "error")
    else:
        add(info, "TEX_FILES", f"expanded {len(files)} TeX file(s) from {entry.name}", "info")

    margins = geometry_margins(combined)
    metrics["margins_cm"] = margins
    if margins is None:
        add(warnings, "MARGIN_UNVERIFIED", "could not resolve all four geometry margins", "warning", str(entry))
    else:
        too_small = {side: round(value, 3) for side, value in margins.items() if value + 1e-6 < args.min_margin_cm}
        if too_small:
            add(errors, "MARGIN_LIMIT", f"margins below {args.min_margin_cm} cm: {too_small}", "error", str(entry))

    label_values = LABEL_RE.findall(combined)
    labels = set(label_values)
    refs = set(REF_RE.findall(combined))
    duplicate_labels = sorted(label for label, count in Counter(label_values).items() if count > 1)
    for label in duplicate_labels:
        target = errors if structure_strict else warnings
        severity = "error" if structure_strict else "warning"
        add(target, "DUPLICATE_LABEL", f"label is defined more than once: {label}", severity)
    for label in sorted(refs - labels):
        add(errors, "UNDEFINED_REF", f"reference points to undefined label: {label}", "error")
    if labels - refs:
        add(warnings, "UNUSED_LABEL", f"{len(labels - refs)} label(s) are not referenced", "warning")

    cite_keys = split_keys(cite_groups)
    bib_keys: set[str] = set(BIBITEM_RE.findall(combined))
    for bib in sorted(paper_dir.rglob("*.bib")):
        text = bib.read_text(encoding="utf-8", errors="replace")
        bib_keys.update(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text))
        bib_keys.update(re.findall(r"\\bibitem\{([^{}]+)\}", text))
    if cite_keys and not bib_keys:
        add(warnings, "BIB_NOT_FOUND", "citations found but no bibliography entries were found", "warning")
    for key in sorted(cite_keys - bib_keys):
        add(errors, "UNDEFINED_CITATION", f"citation key is absent from bibliography: {key}", "error")
    if bib_keys - cite_keys:
        target = errors if structure_strict else warnings
        severity = "error" if structure_strict else "warning"
        add(target, "UNCITED_BIB", f"{len(bib_keys - cite_keys)} bibliography item(s) are not cited", severity)
    first_use = ordered_citation_keys(combined)
    bibliography_keys = bibliography_order(combined, paper_dir, entry)
    metrics["citation_first_use"] = first_use
    metrics["bibliography_order"] = bibliography_keys
    if bibliography_keys:
        cited_bibliography_order = [key for key in bibliography_keys if key in first_use]
        if cited_bibliography_order != first_use:
            add(errors if structure_strict else warnings, "BIB_ORDER", "bibliography order does not match first citation order", "error" if structure_strict else "warning")
    elif first_use:
        add(warnings, "BIB_ORDER_UNVERIFIED", "bibliography output order could not be verified without explicit bibitems or a .bbl file", "warning")

    for file_name, text in files.items():
        if PLACEHOLDER_RE.search(text):
            add(errors, "PLACEHOLDER", "unfinished placeholder text remains", "error", file_name)
        if args.require_anonymous and ANONYMITY_RE.search(text):
            add(errors, "ANONYMITY", "possible author, school, team, student, or contact identity found", "error", file_name)

    for raw in GRAPHICS_RE.findall(combined):
        if resolve_graphic(paper_dir, raw) is None:
            add(errors, "MISSING_GRAPHIC", f"graphic file does not exist: {raw}", "error")

    for env_name, label in (("figure", "figure"), ("table", "table")):
        for match in re.finditer(rf"\\begin\{{{env_name}\*?\}}(.*?)\\end\{{{env_name}\*?\}}", combined, re.S):
            block = match.group(1)
            if not re.search(r"\\caption\s*\{", block):
                add(errors, "MISSING_CAPTION", f"{label} environment has no caption", "error")
            if env_name == "table":
                caption = block.find("\\caption")
                rule = min((index for token in ("\\toprule", "\\midrule", "\\hline") if (index := block.find(token)) >= 0), default=-1)
                if rule >= 0 and caption > rule:
                    add(warnings, "TABLE_CAPTION_POSITION", "table caption appears after the first rule", "warning")
            else:
                include, caption = block.find("\\includegraphics"), block.find("\\caption")
                if include >= 0 and caption >= 0 and caption < include:
                    add(warnings, "FIGURE_CAPTION_POSITION", "figure caption appears before the graphic", "warning")

    audit_artifact_flow(combined, errors, warnings, structure_strict)
    if structure_strict:
        audit_structure(combined, paper_dir, labels, errors, warnings, metrics)

    explicit_log = getattr(args, "log", None)
    log_candidates = [Path(explicit_log).resolve()] if explicit_log else [entry.with_suffix(".log"), paper_dir / "main.log"]
    log_path = next((candidate for candidate in log_candidates if candidate.is_file()), None)
    audit_latex_log(log_path, errors, warnings, metrics, structure_strict)

    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", combined, re.S)
    if not abstract_match:
        add(warnings, "ABSTRACT_MISSING", "no abstract environment found", "warning")
    else:
        abstract_chars = len(plain_text(abstract_match.group(1)))
        metrics["abstract_chars"] = abstract_chars
        if abstract_chars < 80:
            add(warnings, "ABSTRACT_SHORT", f"abstract has only approximately {abstract_chars} visible characters", "warning")
        if abstract_chars > args.abstract_char_warning:
            add(warnings, "ABSTRACT_LONG", f"abstract has approximately {abstract_chars} visible characters", "warning")

    pdf_path = Path(args.pdf).resolve() if args.pdf else None
    if pdf_path:
        pages, error = pdf_metrics(pdf_path)
        metrics["pages"] = pages or 0
        metrics["pdf_mb"] = round(pdf_path.stat().st_size / (1024 * 1024), 3) if pdf_path.is_file() else 0.0
        if error:
            add(warnings, "PDF_UNREADABLE", error, "warning")
        if pages is not None and pages > hard_total_max_pages:
            add(errors, "PAGE_LIMIT", f"PDF has {pages} total pages; hard limit is {hard_total_max_pages}", "error")
        elif pages is not None and pages > args.max_pages + 1:
            message = f"PDF has {pages} total pages; recommended budget is one abstract page plus {args.max_pages} body pages"
            if page_limit_policy == "recommended":
                add(warnings, "PAGE_BUDGET", message, "warning")
            else:
                add(errors, "PAGE_LIMIT", message, "error")
        if pdf_path.is_file() and pdf_path.stat().st_size > args.max_pdf_mb * 1024 * 1024:
            add(errors, "PDF_SIZE", f"PDF is {metrics['pdf_mb']} MiB, limit is {args.max_pdf_mb} MiB", "error")
    else:
        add(warnings, "PDF_NOT_CHECKED", "no --pdf supplied; page count and size were not checked", "warning")

    add(info, "SUMMARY", f"scanned {metrics['sections']} sections, {metrics['figures']} figures, and {metrics['tables']} tables", "info")
    return {"schema_version": 2, "passed": not errors, "errors": errors, "warnings": warnings, "info": info, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--contest-config")
    parser.add_argument("--pdf")
    parser.add_argument("--log", help="optional LaTeX log; defaults to paper/main.log when present")
    parser.add_argument("--output")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--max-pdf-mb", type=float, default=20.0)
    parser.add_argument("--min-margin-cm", type=float, default=2.5)
    parser.add_argument("--abstract-char-warning", type=int, default=1500)
    parser.add_argument("--require-anonymous", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--structure-strict",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enforce the CUMCM V3 paper/evidence contract; auto-enabled for contract v3 or question schema v2",
    )
    args = parser.parse_args()
    result = audit(args)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
