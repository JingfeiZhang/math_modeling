from __future__ import annotations

import argparse
import importlib.util
from importlib.machinery import PathFinder
import json
import os
import platform
import site
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Check:
    name: str
    package: str
    kind: str
    available: bool
    location: str | None = None
    provenance: str | None = None
    user_site_available: bool = False
    user_site_location: str | None = None


def load_requirements(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_import(item: dict, kind: str) -> Check:
    name = str(item["import"])
    spec = importlib.util.find_spec(name)
    package = str(item.get("conda") or item.get("pip") or name)
    location = getattr(spec, "origin", None) if spec else None
    prefix = Path(sys.prefix).resolve()
    in_environment = False
    if location and location not in {"built-in", "frozen"}:
        try:
            Path(location).resolve().relative_to(prefix)
            in_environment = True
        except ValueError:
            in_environment = False
    elif spec is not None:
        locations = list(getattr(spec, "submodule_search_locations", None) or [])
        in_environment = any(_is_within(Path(entry), prefix) for entry in locations)

    user_site = Path(site.getusersitepackages())
    user_spec = PathFinder.find_spec(name, [str(user_site)]) if user_site.is_dir() else None
    user_location = getattr(user_spec, "origin", None) if user_spec else None
    provenance = "environment-prefix" if in_environment else ("external" if spec is not None else "missing")
    return Check(
        name,
        package,
        kind,
        in_environment,
        location,
        provenance,
        user_spec is not None,
        user_location,
    )


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent)
        return True
    except ValueError:
        return False


def collect(requirements: dict) -> list[Check]:
    checks = [check_import(item, "python-core") for item in requirements["core"]["python"]]
    checks.extend(check_import(item, "python-extended") for item in requirements["extended"]["python"])
    for name in requirements["core"]["commands"]:
        location = shutil.which(name)
        checks.append(Check(str(name), str(name), "command", location is not None, location))
    return checks


def build_report(requirements: dict, tier: str) -> dict:
    checks = collect(requirements)
    core_prefix_missing = [item.name for item in checks if not item.available and item.kind in {"python-core", "command"}]
    core_external_local = [
        item.name
        for item in checks
        if not item.available and item.kind == "python-core" and item.user_site_available
    ]
    core_missing = (
        [name for name in core_prefix_missing if name not in core_external_local]
        if tier == "core"
        else core_prefix_missing
    )
    extended_missing = [item.name for item in checks if not item.available and item.kind == "python-extended"]
    required_missing = core_missing + (extended_missing if tier == "full" else [])
    user_site_contamination = [
        {
            "name": item.name,
            "user_site_location": item.user_site_location,
            "environment_available": item.available,
        }
        for item in checks
        if item.kind.startswith("python-") and item.user_site_available
    ]
    warnings = []
    if user_site_contamination:
        warnings.append(
            "User-site packages were detected outside the Conda prefix. Core may use an exact "
            "external-local fallback, but full/extended verification remains prefix-only."
        )
    return {
        "schema_version": 2,
        "environment": os.environ.get("MATHMODEL_SELECTED_ENV", "unknown"),
        "environment_prefix": os.environ.get("MATHMODEL_SELECTED_PREFIX", sys.prefix),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "provenance_policy": (
            "environment-prefix-plus-external-local" if tier == "core" else "environment-prefix-only"
        ),
        "python_no_user_site": bool(sys.flags.no_user_site),
        "user_site_path": site.getusersitepackages(),
        "user_site_contamination": user_site_contamination,
        "warnings": warnings,
        "requested_tier": tier,
        "checks": [asdict(item) for item in checks],
        "core_prefix_missing": core_prefix_missing,
        "core_external_local": core_external_local,
        "core_missing": core_missing,
        "extended_missing": extended_missing,
        "required_missing": required_missing,
        "status": "PASS" if not required_missing else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check one math-modeling environment.")
    parser.add_argument("--tier", choices=("core", "full"), default="core")
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()

    payload = build_report(load_requirements(args.requirements), args.tier)
    for item in payload["checks"]:
        if item["name"] in payload["core_external_local"] and args.tier == "core":
            state = "EXTERNAL_LOCAL"
        else:
            state = "OK" if item["available"] else "MISSING"
        print(f"{state:7} {item['kind']:16} {item['name']}")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if args.allow_missing or payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
