#!/usr/bin/env python
"""Integrate the reviewed C-problem optimization round into formal state."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
Q4_SUMMARY = "experiments/C/Q4/q4-optimization-20260809/q4_formal_summary.json"
Q4_MANIFEST = "experiments/C/Q4/q4-optimization-20260809/formal_run_manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    question_path = ROOT / "problems/C/questions/Q4/question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["method"]["main"] = {
        "name": "72 小时任务 fix-and-optimize 与六区域储能 MILP 受限联合优化",
        "rationale": "以冻结 Q2 排程为可行起点，在高成本、高碳和高时延任务构成的 12 任务邻域中交替调整任务区域/时刻并重求六区域二进制储能 MILP；该结构在保持 50000 条任务硬约束的同时，直接比较任务移动后的储能 recourse。",
        "implementation": "固定 2328--2399 小时代表性窗口、种子 20260809 和单一确定性搜索顺序；对 observed、峰段电价、高碳、低新能源和联合压力五个场景执行 53 次储能 recourse 评估，接受严格改善且全指标不劣的任务移动，并独立复算任务、SOC、充放电互斥、购售电互斥、电能平衡和终端 SOC。结果仅解释为 72 小时局部联合优化，不宣称全时域或全局最优。",
    }
    question["method"]["baseline"] = {
        "name": "冻结 Q2 排程加同场景六区域储能 recourse",
        "implementation": "在相同 72 小时窗口、五个场景和储能边界下保持 Q2 任务排程不变，重新求解同一六区域二进制储能模型，输出同口径成本、购电碳排、正向峰值和新能源利用率。",
        "comparable_output": True,
    }
    question["decisions"] = [
        {
            "id": "q4-decision-optimization-20260809",
            "status": "confirmed",
            "decision": "晋升 72 小时受限联合优化候选；Q1--Q3 优化探针未达预注册门槛，继续保留原冻结主线。",
            "evidence_ref": Q4_SUMMARY,
        }
    ]
    question["evidence"] = {
        "runs": [Q4_MANIFEST],
        "robustness": Q4_SUMMARY,
        "figures": [
            "paper/figure_contracts.yaml#fig-q4-joint-optimization-loop",
            "paper/figure_contracts.yaml#fig-q4-system-profile",
        ],
    }
    question["paper"] = {
        "section": "问题四：72 小时算—储—电受限联合优化",
        "figure_ids": ["fig-q4-joint-optimization-loop", "fig-q4-system-profile"],
    }
    question["status"] = "VERIFIED"
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")

    claims_path = ROOT / "results/C/claims.json"
    claims = load_json(claims_path)
    claims["claims"] = [item for item in claims["claims"] if item.get("question_id") != "Q4"]
    specs = [
        ("Q4-AUDIT-PASS", "$.audit.all_hard_constraints_passed", "72 小时受限联合优化的任务、储能和电网硬约束均通过独立审计；该结论不代表全时域全局最优。", "boolean"),
        ("Q4-OBS-COST-DELTA", "$.observed_72h.cost_delta_CNY", "观测场景下，局部联合候选相对固定任务排程加储能 recourse 的净运行成本差；负值表示按购电减售电收入定义的指标降低。", "CNY"),
        ("Q4-LOWREN-COST-DELTA", "$.low_renewable_72h.cost_delta_CNY", "低新能源场景下，局部联合候选相对顺序基线的净运行成本差。", "CNY"),
        ("Q4-LOWREN-CARBON-DELTA", "$.low_renewable_72h.carbon_delta_tCO2", "低新能源场景下，局部联合候选相对顺序基线的购电碳排差。", "tCO2"),
        ("Q4-JOINT-CARBON-DELTA", "$.joint_stress_72h.carbon_delta_tCO2", "联合压力场景下，局部联合候选相对顺序基线的购电碳排差。", "tCO2"),
        ("Q4-DETERMINISTIC-REPLAY", "$.audit.deterministic_replay_passed", "固定输入、种子和搜索顺序下，Q4 候选排程完成逐字节确定性复跑；这不证明解的唯一性。", "boolean"),
    ]
    claims["claims"].extend({
        "id": claim_id,
        "question_id": "Q4",
        "status": "verified",
        "statement": statement,
        "locator": f"{Q4_SUMMARY}:{locator}",
        "unit": unit,
    } for claim_id, locator, statement, unit in specs)
    dump_json(claims_path, claims)

    review = {
        "schema_version": 1,
        "project_id": "huashu-cup-2026",
        "problem_id": "C",
        "generated_at_utc": now,
        "baseline_claim_sha256": "00dc4ed7af69a13646174a2c2c3bc7d64b58af3011c5cb36b28c4f1288a08c44",
        "decisions": {
            "Q1": {"decision": "RETAIN", "reason": "RMSE and interval-width gates failed", "evidence": "experiments/C/Q1/q1-optimization-20260809/summary.json"},
            "Q2": {"decision": "RETAIN", "reason": "candidate carbon degradation exceeded 0.1%", "evidence": "experiments/C/Q2/q2-optimization-20260809/summary.json"},
            "Q3": {"decision": "RETAIN", "reason": "adaptive-window gain was below 0.1% and export semantics require caution", "evidence": "experiments/C/Q3/q3-review-20260809/q3_adaptive_summary.json"},
            "Q4": {"decision": "PROMOTE", "reason": "all five scenarios non-worse with strict improvement, hard audits and deterministic replay", "evidence": Q4_SUMMARY},
        },
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    dump_json(reports / "C_optimization_review_20260809.json", review)

    state_path = ROOT / "state/decision_log.json"
    state = load_json(state_path)
    state["stages"]["7"].setdefault("strengths", []).append("Q4 五场景 72 小时局部联合优化通过硬约束、非劣性和确定性复跑门槛")
    state["stages"]["7"].setdefault("limitations", []).append("Q1--Q3 性能探针未达预注册门槛；Q4 仅为 12 任务邻域和 72 小时局部联合优化")
    state.setdefault("events", {}).setdefault("log", []).append({
        "type": "optimization_review",
        "timestamp_utc": now,
        "stage": 7,
        "question_id": "Q1-Q4",
        "status": "PROMOTE_Q4_ONLY",
        "evidence": "reports/C_optimization_review_20260809.json",
    })
    dump_json(state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
