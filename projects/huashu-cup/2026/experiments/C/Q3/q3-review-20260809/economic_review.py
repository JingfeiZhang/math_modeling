#!/usr/bin/env python
"""Read-only economic semantic checks for the Q3 adaptive candidate."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


OUT = Path(__file__).resolve().parent
DISPATCH = OUT / "q3_adaptive_dispatch.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    dispatch = pd.read_csv(DISPATCH)
    required = {
        "GridPurchase_MW",
        "GridSell_MW",
        "ElectricityPrice_CNY_per_MWh",
        "SellPrice_CNY_per_MWh",
        "CarbonIntensity_tCO2_per_MWh",
    }
    missing = sorted(required.difference(dispatch.columns))
    if missing:
        raise RuntimeError(f"missing economic columns: {missing}")

    purchase = dispatch["GridPurchase_MW"].astype(float)
    sell = dispatch["GridSell_MW"].astype(float)
    total_cost = float(
        (purchase * dispatch["ElectricityPrice_CNY_per_MWh"].astype(float)
         - sell * dispatch["SellPrice_CNY_per_MWh"].astype(float)).sum()
    )
    purchase_carbon = float(
        (purchase * dispatch["CarbonIntensity_tCO2_per_MWh"].astype(float)).sum()
    )
    flags = {
        "negative_net_cost": bool(total_cost < 0),
        "zero_purchase_carbon": bool(purchase.sum() > 1e-9 and purchase_carbon <= 1e-9),
        "grid_sell_present": bool(sell.sum() > 1e-9),
    }
    result = {
        "schema_version": 1,
        "question_id": "Q3",
        "run_id": "q3-review-20260809",
        "status": "REVIEW_REQUIRED" if any(flags.values()) else "PASS",
        "metrics": {
            "total_net_cost_CNY": total_cost,
            "total_grid_purchase_MWh": float(purchase.sum()),
            "total_grid_sell_MWh": float(sell.sum()),
            "purchase_carbon_tCO2": purchase_carbon,
        },
        "flags": flags,
        "interpretation": "This check does not change the Q3 model; it identifies whether export revenue, degradation cost, and carbon accounting need explicit paper assumptions.",
        "environment": {"python": sys.version, "platform": platform.platform()},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"path": str(DISPATCH.relative_to(OUT.parents[3])).replace("\\", "/"), "sha256": sha256(DISPATCH)},
    }
    (OUT / "economic_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "result_hashes.json")
    hashes = {"schema_version": 1, "files": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in files]}
    (OUT / "result_hashes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
