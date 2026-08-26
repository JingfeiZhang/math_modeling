#!/usr/bin/env python3
"""Aggregate internal AI usage events into a concise four-stage disclosure summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STAGE_KEYS = (
    "problem_analysis",
    "modeling_implementation",
    "experiment_validation",
    "paper_writing",
)

EXACT_PHASE_MAP = {
    "p1": "problem_analysis",
    "p2": "modeling_implementation",
    "p3a": "modeling_implementation",
    "p3b": "modeling_implementation",
    "p4": "experiment_validation",
    "p5": "paper_writing",
    "p6": "paper_writing",
}

KEYWORDS = {
    "problem_analysis": (
        "problem", "decomposition", "literature", "brainstorm", "requirement", "题意", "问题", "拆题", "文献", "思路", "变量", "需求",
    ),
    "modeling_implementation": (
        "model", "algorithm", "formula", "formulation", "code", "solver", "optimization", "模型", "算法", "公式", "推导", "代码", "求解", "优化",
    ),
    "experiment_validation": (
        "experiment", "validation", "verify", "debug", "robust", "sensitivity", "result", "实验", "验证", "核验", "调试", "稳健", "敏感性", "结果",
    ),
    "paper_writing": (
        "paper", "writing", "latex", "figure", "caption", "polish", "论文", "写作", "表达", "润色", "排版", "图表", "摘要",
    ),
}


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def dump_yaml(path: Path, value: dict) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def has_value(entry: dict, field: str) -> bool:
    value = entry.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def find_log(root: Path, policy: dict) -> Path | None:
    cfg = policy.get("log", {})
    candidates = [cfg.get("path")] + list(cfg.get("legacy_paths", []))
    for candidate in candidates:
        if not candidate:
            continue
        path = (root / str(candidate)).resolve()
        if path.is_file():
            return path
    return None


def load_events(path: Path | None) -> list[dict]:
    if path is None:
        return []
    events: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"AI usage line {line_number} must be an object")
        value.setdefault("_line_number", line_number)
        events.append(value)
    return events


def normalize_strings(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def classify_event(event: dict) -> str | None:
    explicit = str(event.get("disclosure_stage") or "").strip().lower()
    if explicit in STAGE_KEYS:
        return explicit

    phase = str(event.get("stage") or "").strip().lower()
    if phase in EXACT_PHASE_MAP:
        return EXACT_PHASE_MAP[phase]

    roles = " ".join(normalize_strings(event.get("ai_role")))
    haystack = " ".join(
        str(event.get(name) or "")
        for name in ("stage", "purpose", "prompt_summary", "question")
    ) + " " + roles
    lowered = haystack.lower()
    scores = {key: sum(1 for keyword in keywords if keyword.lower() in lowered) for key, keywords in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def event_identifier(event: dict) -> str:
    return str(event.get("event_id") or f"line-{event.get('_line_number', '?')}")


def verification_text(value: Any) -> list[str]:
    if isinstance(value, dict):
        result = []
        for key in ("status", "method", "methods", "note", "notes"):
            result.extend(normalize_strings(value.get(key)))
        return result
    return normalize_strings(value)


def aggregate(root: Path, policy_path: Path, mode: str) -> dict:
    policy = load_yaml(policy_path)
    log_path = find_log(root, policy)
    events = load_events(log_path)
    cfg = policy.get("aggregation", {})
    purpose_limit = int(cfg.get("purposes_per_stage_max", 6))
    theme_limit = int(cfg.get("prompt_themes_per_stage_max", 2))
    human_limit = int(cfg.get("human_actions_per_stage_max", 4))

    stages = {
        key: {
            "used": False,
            "event_count": 0,
            "ai_roles": [],
            "purposes": [],
            "prompt_themes": [],
            "human_actions": [],
            "verification_notes": [],
        }
        for key in STAGE_KEYS
    }
    tools: list[dict] = []
    unclassified: list[str] = []

    for event in events:
        tool = str(event.get("tool") or "").strip()
        model = str(event.get("model_version") or "").strip()
        pair = {"tool": tool, "model_version": model}
        if tool and model and pair not in tools:
            tools.append(pair)

        stage_key = classify_event(event)
        if stage_key is None:
            unclassified.append(event_identifier(event))
            continue

        stage = stages[stage_key]
        stage["used"] = True
        stage["event_count"] += 1
        for role in normalize_strings(event.get("ai_role")):
            if role not in stage["ai_roles"]:
                stage["ai_roles"].append(role)
        purpose = str(event.get("purpose") or "").strip()
        if purpose and purpose not in stage["purposes"] and len(stage["purposes"]) < purpose_limit:
            stage["purposes"].append(purpose)
        theme = str(event.get("prompt_summary") or "").strip()
        if theme and theme not in stage["prompt_themes"] and len(stage["prompt_themes"]) < theme_limit:
            stage["prompt_themes"].append(theme)
        modification = str(event.get("human_modification") or "").strip()
        if modification and modification not in stage["human_actions"] and len(stage["human_actions"]) < human_limit:
            stage["human_actions"].append(modification)
        for note in verification_text(event.get("human_verification")):
            if note not in stage["verification_notes"] and len(stage["verification_notes"]) < human_limit:
                stage["verification_notes"].append(note)

    return {
        "schema_version": 1,
        "mode": mode,
        "source_log": str(log_path.relative_to(root)).replace("\\", "/") if log_path else None,
        "tools": tools,
        "stages": stages,
        "unclassified_events": unclassified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--mode", choices=("used", "not_used"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    policy_path = args.policy.resolve()
    policy = load_yaml(policy_path)
    output_cfg = policy.get("aggregation", {}).get("output", "output/ai/stage_summary.yaml")
    output = args.output.resolve() if args.output else (root / output_cfg).resolve()
    summary = aggregate(root, policy_path, args.mode)
    dump_yaml(output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
