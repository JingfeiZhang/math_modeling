from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SPRINT_ID = "sprint-20260808T083901900797Z"
TASK_ID = "figure-q2"
STAGING = PROJECT_ROOT / "sprints" / SPRINT_ID / "staging" / "figure-q2"
TASK_PACKAGE = PROJECT_ROOT / "sprints" / SPRINT_ID / "tasks" / "solver-q1.json"
MERGED = PROJECT_ROOT / "sprints" / "sprint-20260808T031146908286Z" / "merged" / "solver-q2"
COMPAT = PROJECT_ROOT / "experiments" / "C" / "Q2" / "q2-full-compat-20260808"
HOURLY = MERGED / "q2_full_hourly_profiles.csv"
BLOCKS = MERGED / "q2_full_block_robustness.csv"
SUMMARY = COMPAT / "q2_compat_summary.json"
PNG_DPI = 400
WIDTH_MM = 158.0
HEIGHT_MM = 104.0
PALETTE_ID = "journal-spectrum-v2"

COLORS = {
    "primary": "#5292F7",
    "baseline": "#79CAFB",
    "improved": "#4EA660",
    "highlight": "#F7A24F",
    "risk": "#E95351",
    "auxiliary": "#AA77E9",
    "accent": "#CC247C",
    "caution": "#FBEB66",
    "ink": "#1F2933",
    "grid": "#D9DEE5",
    "fill": "#EAF0F4",
    "background": "#FFFFFF",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_task_inputs() -> tuple[dict, list[dict]]:
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8"))
    if task.get("task_id") != TASK_ID or task.get("question") != "Q2":
        raise RuntimeError(f"unexpected task package identity: {task.get('task_id')!r}")
    checks = []
    for item in task.get("input_hashes", []):
        path = PROJECT_ROOT / str(item["path"])
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "path": item["path"],
                "expected": item["sha256"],
                "actual": actual,
                "match": actual == item["sha256"],
            }
        )
    stale = [item for item in checks if not item["match"]]
    if stale:
        raise RuntimeError(f"stale or changed sprint input: {stale}")
    return task, checks


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Microsoft YaHei"],
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "axes.linewidth": 0.7,
            "axes.edgecolor": COLORS["ink"],
            "axes.labelcolor": COLORS["ink"],
            "xtick.color": COLORS["ink"],
            "ytick.color": COLORS["ink"],
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": COLORS["background"],
            "figure.facecolor": COLORS["background"],
        }
    )


def normalize_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    mapping: dict[str, str] = {}

    def canonical(source: str) -> str:
        prefix = "clip" if source.startswith("p") else "marker"
        mapping.setdefault(source, f"{prefix}-{len(mapping) + 1:04d}")
        return mapping[source]

    text = re.sub(r'id="([pm][0-9a-f]{8,})"', lambda m: f'id="{canonical(m.group(1))}"', text)
    text = re.sub(r"url\(#([pm][0-9a-f]{8,})\)", lambda m: f"url(#{canonical(m.group(1))})", text)
    text = re.sub(r'xlink:href="#([pm][0-9a-f]{8,})"', lambda m: f'xlink:href="#{canonical(m.group(1))}"', text)
    path.write_text(text, encoding="utf-8", newline="\n")


def layout_qa(fig) -> dict:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas_box = fig.bbox
    tick_ids = {
        id(label)
        for axis in fig.axes
        for label in [*axis.get_xticklabels(), *axis.get_yticklabels()]
    }
    text_items = []
    clipped = []
    for item in fig.findobj(match=matplotlib.text.Text):
        if not item.get_visible() or not item.get_text().strip() or id(item) in tick_ids:
            continue
        box = item.get_window_extent(renderer=renderer)
        if box.width <= 0 or box.height <= 0:
            continue
        if box.x0 < canvas_box.x0 - 2 or box.x1 > canvas_box.x1 + 2 or box.y0 < canvas_box.y0 - 2 or box.y1 > canvas_box.y1 + 2:
            clipped.append(item.get_text())
        text_items.append((item.get_text(), box))
    collisions = []
    for index, (left_label, left_box) in enumerate(text_items):
        for right_label, right_box in text_items[index + 1 :]:
            overlap = matplotlib.transforms.Bbox.intersection(left_box, right_box)
            if overlap is not None and overlap.width * overlap.height > 4:
                collisions.append((left_label, right_label))
    if clipped or collisions:
        raise RuntimeError(f"figure layout QA failed: clipped={clipped}, collisions={collisions[:3]}")
    return {"passed": True, "text_count": len(text_items), "collision_count": 0, "clipped_count": 0}


def read_evidence() -> tuple[dict, pd.DataFrame, dict, list[dict]]:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    hourly = pd.read_csv(HOURLY)
    blocks = pd.read_csv(BLOCKS)
    if summary.get("status") != "PASS" or summary.get("question_id") != "Q2":
        raise RuntimeError("frozen Q2 compatibility summary is not PASS")
    if set(hourly["Method"].astype(str)) != {
        summary["methods"]["main"],
        summary["methods"]["baseline"],
    }:
        raise RuntimeError("hourly profile methods disagree with frozen summary")
    expected_methods = [summary["methods"]["baseline"], summary["methods"]["main"]]
    if hourly["Hour"].nunique() != 2406 or hourly["Region"].nunique() != 6:
        raise RuntimeError("hourly profile does not cover 2406 hours and six regions")
    expected_rows = 2406 * 6 * len(expected_methods)
    if len(hourly) != expected_rows:
        raise RuntimeError(f"unexpected hourly profile row count: {len(hourly)}")
    if blocks["block_id"].nunique() != 6:
        raise RuntimeError("operation-block robustness evidence is incomplete")
    return summary, hourly, blocks, expected_methods


def derive_cost_index(summary: dict, hourly: pd.DataFrame, expected_methods: list[str]) -> tuple[pd.DataFrame, dict]:
    grouped = (
        hourly.groupby(["Method", "Hour"], as_index=False)["ElectricityCost_CNY"]
        .sum()
        .sort_values(["Method", "Hour"])
    )
    wide = grouped.pivot(index="Hour", columns="Method", values="ElectricityCost_CNY").sort_index()
    if list(wide.columns) != sorted(expected_methods):
        raise RuntimeError("pivoted hourly methods are not stable")
    baseline = summary["methods"]["baseline"]
    main = summary["methods"]["main"]
    if set(wide.columns) != {baseline, main}:
        raise RuntimeError("pivoted hourly methods disagree with summary")
    index = pd.DataFrame(
        {
            "Hour": wide.index.to_numpy(dtype=int),
            "FIFO baseline": 100.0,
            "Rolling exchange": 100.0 * wide[main].cumsum().to_numpy() / wide[baseline].cumsum().to_numpy(),
        }
    )
    endpoint_delta = float(index["Rolling exchange"].iloc[-1] - 100.0)
    frozen_delta = float(summary["comparison_vs_fifo"]["cost_change_pct"])
    if not math.isclose(endpoint_delta, frozen_delta, rel_tol=1e-11, abs_tol=1e-9):
        raise RuntimeError(f"derived endpoint cost change disagrees with frozen summary: {endpoint_delta} != {frozen_delta}")
    diagnostics = {
        "hour_count": int(len(index)),
        "region_count": int(hourly["Region"].nunique()),
        "baseline_total_cost_cny": float(wide[baseline].sum()),
        "main_total_cost_cny": float(wide[main].sum()),
        "endpoint_index_percent": float(index["Rolling exchange"].iloc[-1]),
        "endpoint_cost_change_percent": endpoint_delta,
        "minimum_main_index_percent": float(index["Rolling exchange"].min()),
        "maximum_main_index_percent": float(index["Rolling exchange"].max()),
        "main_below_baseline_all_hours": bool((index["Rolling exchange"] <= 100.0 + 1e-12).all()),
    }
    return index, diagnostics


def make_figure(index: pd.DataFrame, diagnostics: dict):
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), facecolor=COLORS["background"])
    ax = fig.add_axes([0.165, 0.19, 0.77, 0.66], facecolor=COLORS["background"])
    x = index["Hour"].to_numpy(dtype=float)
    baseline = index["FIFO baseline"].to_numpy(dtype=float)
    main = index["Rolling exchange"].to_numpy(dtype=float)
    marker_hours = [hour for hour in (0, 600, 1200, 1800, 2400) if hour in set(index["Hour"])]
    marker_positions = index["Hour"].isin(marker_hours)
    ax.plot(x, baseline, color=COLORS["baseline"], linestyle="--", linewidth=1.35, zorder=2)
    ax.plot(x, main, color=COLORS["primary"], linestyle="-", linewidth=1.55, zorder=3)
    ax.scatter(x[marker_positions], baseline[marker_positions], color=COLORS["baseline"], marker="s", s=16, zorder=4)
    ax.scatter(x[marker_positions], main[marker_positions], color=COLORS["primary"], marker="o", s=17, zorder=4)
    ax.axhline(100.0, color=COLORS["grid"], linewidth=0.65, zorder=1)
    ax.set_xlim(float(x.min()), float(x.max()) + 500.0)
    lo = min(float(main.min()) - 0.35, 99.4)
    ax.set_ylim(lo, 100.42)
    ax.set_xlabel("Hour from task horizon (h)")
    ax.set_ylabel("Cumulative facility-energy cost relative to FIFO (%)")
    ax.set_xticks(marker_hours)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.yaxis.grid(True, color=COLORS["grid"], linewidth=0.45, alpha=0.55)
    ax.xaxis.grid(False)
    label_x = float(x[-1]) - 300.0
    ax.text(label_x, float(main[-1]), f"Rolling exchange ({diagnostics['endpoint_cost_change_percent']:+.3f}%)", color=COLORS["primary"], va="center", ha="left", fontsize=8.0)
    ax.text(label_x, 100.0, "FIFO baseline", color=COLORS["baseline"], va="center", ha="left", fontsize=8.0)
    return fig


def save_exports(fig) -> dict:
    outputs = {
        "pdf": STAGING / "fig_q2_dispatch_comparison.pdf",
        "svg": STAGING / "fig_q2_dispatch_comparison.svg",
        "png": STAGING / "fig_q2_dispatch_comparison.png",
    }
    qa = layout_qa(fig)
    fig.savefig(outputs["pdf"], metadata={"Creator": "math-modeling-workbench", "CreationDate": None, "ModDate": None})
    fig.savefig(outputs["svg"], metadata={"Creator": "math-modeling-workbench", "Date": None})
    normalize_svg(outputs["svg"])
    fig.savefig(outputs["png"], dpi=PNG_DPI, metadata={"Software": "math-modeling-workbench"})
    plt.close(fig)
    from PIL import Image
    from pypdf import PdfReader

    with Image.open(outputs["png"]) as image:
        png_size = list(image.size)
        png_dpi = [float(value) for value in image.info.get("dpi", (None, None))]
        if png_size[0] < 2400 or png_size[1] < 1500 or not all(value >= 399.0 for value in png_dpi):
            raise RuntimeError(f"PNG export QA failed: size={png_size}, dpi={png_dpi}")
    pdf_pages = len(PdfReader(str(outputs["pdf"]).replace("\\", "/")).pages)
    if pdf_pages != 1:
        raise RuntimeError(f"PDF must contain exactly one page, got {pdf_pages}")
    svg_text = outputs["svg"].read_text(encoding="utf-8")
    if "<text" not in svg_text or "path" not in svg_text:
        raise RuntimeError("SVG export does not retain editable text/vector paths")
    return {
        "paths": {kind: relative(path) for kind, path in outputs.items()},
        "sha256": {kind: sha256(path) for kind, path in outputs.items()},
        "physical_size_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "png_size_px": png_size,
        "png_dpi": png_dpi,
        "pdf_page_count": pdf_pages,
        "svg_editable_text": True,
        "layout_qa": qa,
    }


def write_outputs(task: dict, checks: list[dict], summary: dict, hourly: pd.DataFrame, blocks: pd.DataFrame, diagnostics: dict, exports: dict) -> None:
    summary_path = relative(SUMMARY)
    hourly_path = relative(HOURLY)
    blocks_path = relative(BLOCKS)
    script_path = relative(Path(__file__).resolve())
    claim_id = "Q2-FULL-COST-CHANGE-PCT"
    contract = {
        "contract_version": "2.0",
        "id": "fig-q2-dispatch-comparison",
        "question_id": "Q2",
        "claim_id": claim_id,
        "claim_status": "frozen",
        "core_conclusion": "The deterministic rolling exchange schedule remains below the same-input FIFO cumulative facility-energy cost index across the supplied horizon, with the endpoint tied to the frozen Q2 cost-change claim.",
        "core_message": "A single cumulative cost index makes the full-horizon comparison readable while preserving the FIFO reference and the bounded-heuristic interpretation.",
        "evidence_chain": [
            {"locator": f"{summary_path}:$.comparison_vs_fifo.cost_change_pct", "sha256": sha256(SUMMARY), "fields": ["comparison_vs_fifo.cost_change_pct"]},
            {"locator": f"{hourly_path}:Method in {{{summary['methods']['baseline']},{summary['methods']['main']}}}; Hour 0--{diagnostics['hour_count'] - 1}; Region all", "sha256": sha256(HOURLY), "fields": ["Method", "Hour", "Region", "ElectricityCost_CNY"]},
            {"locator": f"{blocks_path}:block_id; cost_change_pct", "sha256": sha256(BLOCKS), "fields": ["block_id", "cost_change_pct", "candidate_completion_rate", "candidate_SLA_violation_rate"]},
        ],
        "kind": "data",
        "archetype": "model-comparison",
        "backend": "python",
        "target_size_profile": "contest-body",
        "palette_id": PALETTE_ID,
        "color_encoding": [
            {"role": "main_model", "meaning": "deterministic rolling exchange heuristic", "secondary_encoding": "solid line + circle marker"},
            {"role": "baseline", "meaning": "same-input FIFO latency-feasible baseline", "secondary_encoding": "dashed line + square marker"},
            {"role": "reference", "meaning": "FIFO normalized index at 100%", "secondary_encoding": "neutral horizontal reference line"},
        ],
        "visual_hierarchy": {
            "primary_evidence": "Cumulative facility-energy cost index of main schedule versus FIFO.",
            "secondary_context": "FIFO=100% reference and endpoint annotation derived from frozen evidence.",
            "deemphasized": "Light horizontal grid and neutral reference rule; no unneeded decorative layers.",
        },
        "source_data": [hourly_path, summary_path, blocks_path],
        "source_script": script_path,
        "outputs": {
            "pdf": "paper/figures/fig_q2_dispatch_comparison.pdf",
            "svg": "paper/figures/fig_q2_dispatch_comparison.svg",
            "png": "paper/figures/fig_q2_dispatch_comparison.png",
            "png_dpi": PNG_DPI,
        },
        "baseline": "FIFO cumulative facility-energy cost normalized to 100%; same input, constraints, and output class.",
        "axes": [
            {"variable": "Hour from task horizon", "unit": "h"},
            {"variable": "Cumulative facility-energy cost relative to FIFO", "unit": "%"},
        ],
        "caption": "Cumulative facility-energy cost index over the 0--2405 h supplied horizon. The rolling exchange heuristic is compared with the same-input FIFO baseline normalized to 100%; endpoint annotation is generated from the frozen Q2 cost-change evidence. This comparison does not claim global optimality or separate the effect of storage decisions.",
        "panel_map": [{"panel": "main", "role": "primary comparison evidence", "subclaim": "The bounded deterministic exchange schedule has a lower cumulative facility-energy cost than FIFO for the supplied horizon."}],
        "statistics": [
            f"{diagnostics['hour_count']} hourly observations per method after aggregation over {diagnostics['region_count']} regions",
            "Cumulative index = 100 * cumulative ElectricityCost_CNY(method) / cumulative ElectricityCost_CNY(FIFO)",
            "Endpoint delta and all plotted values are derived from frozen JSON/CSV evidence; no manual values",
        ],
        "statistics_report": {
            "sample_size": f"{diagnostics['hour_count']} hours x {diagnostics['region_count']} regions per method",
            "center": "deterministic cumulative sum; endpoint index and trajectory extrema",
            "interval": "not applicable; no stochastic interval is plotted",
            "test": "not applicable; paired deterministic same-input trajectory",
            "multiplicity": "not applicable",
        },
        "data_integrity": {
            "source_hashes": [
                {"path": hourly_path, "sha256": sha256(HOURLY)},
                {"path": summary_path, "sha256": sha256(SUMMARY)},
                {"path": blocks_path, "sha256": sha256(BLOCKS)},
            ],
            "transformation": "Read-only grouping by Method and Hour across Region, cumulative summation of ElectricityCost_CNY, and normalization to the FIFO cumulative cost; the endpoint is cross-checked against the frozen Q2 summary.",
            "manual_values_forbidden": True,
        },
        "label_strategy": {"mode": "direct-endpoint-labels", "collision_checked": bool(exports["layout_qa"]["passed"]), "justification": "Series are labeled at the right edge; line style and marker shape remain available in grayscale."},
        "rasterized_layers": [],
        "review_risks": [
            "Cumulative normalization emphasizes the horizon-wide comparison and can hide local regional or hourly variation.",
            "The figure reports the cost comparison only; carbon, latency, and fixed-schedule stress probes remain separate evidence.",
            "The main method is a bounded deterministic rolling exchange heuristic, not a global or MILP-optimal solution.",
            "A lower cumulative cost does not establish causal attribution or transfer to altered inputs.",
        ],
        "qa_report": exports,
        "multipanel_justification": "Single primary axes are sufficient for the frozen Q2 cost-change claim; adding cost, carbon, and latency would mix units and dilute the claim.",
        "final_width_mm": exports["physical_size_mm"]["width"],
        "min_font_pt": 8,
        "status": "staging/supporting",
        "contest_evidence_eligible": False,
        "synthetic_fixture": False,
    }
    proposal = {
        "schema_version": 2,
        "sprint_id": SPRINT_ID,
        "status": "staging/supporting",
        "contest_evidence_eligible": False,
        "palette_id": PALETTE_ID,
        "formal_claim_ids": [claim_id],
        "contracts": [contract],
    }
    proposal_path = STAGING / "figure_contract_proposals.yaml"
    proposal_path.write_text(yaml.safe_dump(proposal, allow_unicode=True, sort_keys=False), encoding="utf-8")
    expected_paths = [
        "figure_contract_proposals.yaml",
        "generate_q2_figures.py",
        "fig_q2_dispatch_comparison.pdf",
        "fig_q2_dispatch_comparison.svg",
        "fig_q2_dispatch_comparison.png",
    ]
    artifacts = [{"path": relative(STAGING / item), "sha256": sha256(STAGING / item)} for item in expected_paths]
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "role": "figure",
        "status": "SUCCESS",
        "attempt": int(task.get("attempt", 1)),
        "target_gate": "G5",
        "input_hashes": task.get("input_hashes", []),
        "input_scope": task.get("allowed_read_paths", []),
        "written_paths": [relative(STAGING / item) for item in [*expected_paths, "handoff.json"]],
        "artifacts": artifacts,
        "formal_state_modified": False,
        "frozen_claims_used": [claim_id],
        "gate_result": {
            "gate": "G5",
            "passed": True,
            "status": "STAGING_ONLY",
            "checks": [
                "All task-package input hashes were rechecked before reading evidence.",
                "Hourly CSV aggregation covers the supplied 0--2405 h horizon and six regions for both methods.",
                "Derived endpoint cost change matches the frozen Q2 summary primitive.",
                "PDF is one page, SVG retains editable text/vector content, and PNG is exported at 400 dpi.",
                "Single primary plotting area, journal-spectrum-v2 palette, and line/marker secondary encodings pass local QA.",
            ],
            "visual_qa": exports,
        },
        "blocking_items": [
            "Formal paper/figure_contracts.yaml remains root-owned and unchanged.",
            "Formal figure output paths are declared in the proposal and require root merge before G5 validation.",
        ],
        "warnings": [
            "The figure supports the frozen cost-change claim only; it is not evidence of global optimality.",
            "Cumulative cost normalization does not replace the separate carbon, latency, or stress-probe evidence.",
        ],
        "generated_at_utc": utcnow(),
    }
    (STAGING / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    configure_style()
    task, checks = validate_task_inputs()
    STAGING.mkdir(parents=True, exist_ok=True)
    summary, hourly, blocks, methods = read_evidence()
    index, diagnostics = derive_cost_index(summary, hourly, methods)
    exports = save_exports(make_figure(index, diagnostics))
    write_outputs(task, checks, summary, hourly, blocks, diagnostics, exports)
    print(json.dumps({"status": "SUCCESS", "staging": relative(STAGING), "figure": "fig-q2-dispatch-comparison", "diagnostics": diagnostics, "exports": exports}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
