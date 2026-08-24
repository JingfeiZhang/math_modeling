"""Normalize the promoted Q2 formal copy without touching immutable sprints."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "projects" / "huashu-cup" / "2026" / "experiments" / "C" / "Q2" / "q2-direct-20260808"
OLD_METHOD = "full_horizon_rolling_shadow_exchange::lagrangian_balanced"
NEW_METHOD = "fixed_weight_bounded_rolling_local_exchange_heuristic"


def replace(value):
    if isinstance(value, dict):
        return {key: replace(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace(item) for item in value]
    if value == OLD_METHOD:
        return NEW_METHOD
    if value == "lagrangian_balanced":
        return "fixed_weight_balanced"
    return value


def main() -> int:
    targets = [Q2 / "models" / "full_horizon", Q2 / "sensitivity"]
    changed: list[str] = []
    for base in targets:
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() == ".json":
                value = json.loads(path.read_text(encoding="utf-8"))
                normalized = replace(value)
                if normalized != value:
                    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    changed.append(path.relative_to(Q2).as_posix())
            elif path.suffix.lower() == ".csv":
                text = path.read_text(encoding="utf-8")
                normalized = text.replace(OLD_METHOD, NEW_METHOD).replace(",lagrangian_balanced,", ",fixed_weight_balanced,")
                if normalized != text:
                    path.write_text(normalized, encoding="utf-8")
                    changed.append(path.relative_to(Q2).as_posix())
    report = {
        "status": "PASS",
        "formal_method": NEW_METHOD,
        "formal_method_zh": "固定权重有界滚动局部交换启发式",
        "source_method_label_retained_only_in_compat_provenance": OLD_METHOD,
        "changed_files": changed,
        "sprints_modified": False,
    }
    (Q2 / "method_name_normalization.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
