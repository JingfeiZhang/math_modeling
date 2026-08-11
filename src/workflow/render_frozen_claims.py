#!/usr/bin/env python3
"""Render verified frozen claims into LaTeX macros and a writing handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def escape_latex(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def evidence_path(root: Path, locator: str) -> Path:
    raw = locator.split(":", 1)[0]
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--problem", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    claims_path = root / "results" / args.problem / "claims.json"
    payload = json.loads(claims_path.read_text(encoding="utf-8"))
    claims = [item for item in payload.get("claims", []) if item.get("status") == "frozen"]
    if not claims:
        raise SystemExit("no frozen claims are available")
    for claim in claims:
        path = evidence_path(root, str(claim.get("locator", "")))
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if digest != claim.get("evidence_sha256"):
            raise SystemExit(f"frozen claim evidence changed: {claim.get('id')}")
    generated = root / "paper" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    lines = [
        "% Generated from frozen evidence. Do not edit.",
        r"\providecommand{\FrozenClaim}[1]{%",
        r"  \ifcsname mathmodelclaim@#1\endcsname",
        r"    \csname mathmodelclaim@#1\endcsname",
        r"  \else",
        r"    \PackageError{mathmodel}{Frozen claim #1 has not been generated}{}%",
        r"  \fi",
        r"}",
        r"\providecommand{\FrozenClaimUnit}[1]{%",
        r"  \ifcsname mathmodelclaimunit@#1\endcsname",
        r"    \csname mathmodelclaimunit@#1\endcsname",
        r"  \else",
        r"    \PackageError{mathmodel}{Frozen claim unit #1 has not been generated}{}%",
        r"  \fi",
        r"}",
        r"\providecommand{\ClaimBoolean}[1]{\ifstrequal{\FrozenClaim{#1}}{True}{通过}{未通过}}",
        r"\providecommand{\ClaimPass}[1]{\ClaimBoolean{#1}}",
    ]
    handoff = {"schema_version": 1, "problem_id": args.problem, "questions": {}}
    for claim in claims:
        identifier = str(claim["id"])
        if not re.fullmatch(r"[A-Za-z0-9._-]+", identifier):
            raise SystemExit(f"claim id is not TeX-safe: {identifier}")
        lines.append(rf"\expandafter\def\csname mathmodelclaim@{identifier}\endcsname{{{escape_latex(claim.get('value'))}}}")
        lines.append(rf"\expandafter\def\csname mathmodelclaimunit@{identifier}\endcsname{{{escape_latex(claim.get('unit'))}}}")
        handoff["questions"].setdefault(str(claim.get("question_id")), []).append(claim)
    (generated / "frozen_claims.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (generated / "claim_handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"claims": len(claims), "tex": "paper/generated/frozen_claims.tex", "handoff": "paper/generated/claim_handoff.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
