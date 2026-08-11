#!/usr/bin/env python3
"""Generate the twelve governed MATLAB Figure Contracts for Problem C."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    report = json.loads((ROOT / "paper/matlab/reports/input_hashes.json").read_text(encoding="utf-8"))
    hashes = {item["path"]: item["sha256"] for item in report["input_hashes"]}
    claims = json.loads((ROOT / "results/C/claims.json").read_text(encoding="utf-8"))["claims"]
    frozen_ids = {item["id"] for item in claims if item.get("status") == "frozen"}

    q1_workload = "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/workload_panel.csv"
    q1_blind = "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/blind_test_predictions.csv"
    q1_series = "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/metrics_by_series.csv"
    q1_metrics = "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/metrics_summary.json"
    q1_schedule = "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/optimized_schedule.csv"
    q1_resource = "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/resource_audit.csv"
    q1_audit = "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/constraint_audit.json"
    q1_sched_metrics = "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/scheduling_metrics.json"
    q2_profiles = "experiments/C/Q2/q2-direct-20260808/models/full_horizon/q2_full_hourly_profiles.csv"
    q2_fifo = "experiments/C/Q2/q2-direct-20260808/models/full_horizon/q2_full_baseline_schedule.csv"
    q2_main = "experiments/C/Q2/q2-direct-20260808/models/full_horizon/q2_full_candidate_schedule.csv"
    q2_summary = "experiments/C/Q2/q2-full-compat-20260808/q2_compat_summary.json"
    q3_dispatch = "experiments/C/Q3/q3-direct-20260808/models/rolling_milp/q3_dispatch.csv"
    q3_windows = "experiments/C/Q3/q3-direct-20260808/models/rolling_milp/q3_comparison_summary.csv"
    q3_audit = "experiments/C/Q3/q3-full-audit-fix-20260809/summary.json"
    q4_metrics = "experiments/C/Q4/q4-optimization-20260809/q4_joint_metrics.csv"
    q4_summary = "experiments/C/Q4/q4-optimization-20260809/q4_formal_summary.json"
    q4_main = "experiments/C/Q4/q4-optimization-20260809/q4_joint_observed_joint_candidate_dispatch.csv"
    q4_base = "experiments/C/Q4/q4-optimization-20260809/q4_joint_observed_sequential_baseline_dispatch.csv"

    def contract(
        identifier: str,
        question: str,
        claim: str,
        archetype: str,
        message: str,
        sources: list[tuple[str, list[str]]],
        script: str,
        baseline: str,
        axes: list[dict[str, str]],
        caption: str,
        statistics: list[str],
        sample_size: str,
        center: str,
        interval: str,
        test: str,
        risks: list[str],
        colors: list[dict[str, str]],
        label_mode: str = "external-legend",
        height: float = 104.0,
        panels: list[dict[str, str]] | None = None,
        multipanel: str | None = None,
    ) -> dict:
        if claim not in frozen_ids:
            raise ValueError(f"Figure {identifier} references non-frozen claim {claim}")
        for path, _ in sources:
            if path not in hashes:
                raise ValueError(f"Figure {identifier} source has no formal input hash: {path}")
        stem = identifier
        item = {
            "contract_version": "2.0",
            "id": identifier,
            "question_id": question,
            "claim_id": claim,
            "claim_status": "frozen",
            "status": "formal_evidence",
            "contest_evidence_eligible": True,
            "synthetic_fixture": False,
            "core_conclusion": message,
            "core_message": message,
            "evidence_chain": [
                {"locator": path, "sha256": hashes[path], "fields": fields}
                for path, fields in sources
            ],
            "kind": "data",
            "archetype": archetype,
            "backend": "matlab",
            "target_size_profile": "contest-body",
            "palette_id": "journal-spectrum-v2",
            "color_encoding": colors,
            "visual_hierarchy": {
                "primary_evidence": message,
                "secondary_context": baseline,
                "deemphasized": "网格、背景和辅助标记仅承担定位作用，不覆盖数据轨迹。",
            },
            "source_data": [path for path, _ in sources],
            "source_script": script,
            "outputs": {
                "pdf": f"paper/figures/{stem}.pdf",
                "svg": f"paper/figures/{stem}.svg",
                "png": f"paper/figures/{stem}.png",
                "png_dpi": 400,
            },
            "baseline": baseline,
            "axes": axes,
            "caption": caption,
            "panel_map": panels or [{"panel": "main", "role": "主要证据区", "subclaim": message}],
            "statistics": statistics,
            "statistics_report": {
                "sample_size": sample_size,
                "center": center,
                "interval": interval,
                "test": test,
                "multiplicity": "不进行多重假设检验；图中比较均为预先定义的描述性或同输入基线比较。",
            },
            "data_integrity": {
                "source_hashes": [{"path": path, "sha256": hashes[path]} for path, _ in sources],
                "transformation": caption,
                "manual_values_forbidden": True,
            },
            "label_strategy": {
                "mode": label_mode,
                "collision_checked": True,
                "justification": "图例或色条置于数据区外或空白区；直接标签经边界和重叠检查。",
            },
            "rasterized_layers": [],
            "review_risks": risks,
            "final_width_mm": 158.0,
            "final_height_mm": height,
            "min_font_pt": 8,
        }
        if multipanel:
            item["multipanel_justification"] = multipanel
        return item

    main_color = {"role": "main_model", "meaning": "主模型或候选", "secondary_encoding": "实线与三角标记"}
    baseline_color = {"role": "baseline", "meaning": "同输入基线", "secondary_encoding": "虚线与方形标记"}
    risk_color = {"role": "risk_or_error", "meaning": "正向压力、充电或迁入", "secondary_encoding": "虚线、正号或暖色端"}

    figures = [
        contract(
            "fig-q1-weekly-demand-structure", "Q1", "Q1-FCST-TEST-WAPE", "weekly-structure-heatmap",
            "18 条底层序列具有不同的周内小时结构；归一化图只描述模式，不比较绝对规模。",
            [(q1_workload, ["ArrivalHour", "SourceRegion", "TaskType", "GPU_Workload_GPUh"])],
            "paper/matlab/figures/fig_q1_weekly_demand_structure.m", "无性能基线；每条序列独立按经验 95% 分位归一化。",
            [{"variable": "周内小时", "unit": "h"}, {"variable": "区域-任务类型序列", "unit": "类别"}],
            "每条序列按自身经验 95% 分位归一化，并在重复周的同一周内小时取中位数；颜色不代表序列间绝对工作量。",
            ["18 条序列", "168 个周内小时", "重复周中位数", "序列内 95% 分位归一化"],
            "18×2400 条底层序列小时记录", "同一周内小时的跨周中位数", "不适用", "不适用",
            ["不得比较序列绝对规模", "不得将描述性周结构写成性能改进"],
            [{"role": "normalized_workload", "meaning": "序列内相对工作量", "secondary_encoding": "色条连续刻度"}], "external-legend", 112.0,
        ),
        contract(
            "fig-q1-blind-forecast-interval", "Q1", "Q1-FCST-TEST-COVERAGE", "prediction-interval",
            "固定盲测 24 h 中，系统实际工作量、主模型、季节基线与底层区间汇总可同时复核。",
            [(q1_blind, ["period", "hour", "actual_gpu_h", "baseline_gpu_h", "main_gpu_h", "main_lower_95_gpu_h", "main_upper_95_gpu_h"]), (q1_metrics, ["summaries.blind_test.shared_hgbr_reconciled.empirical_coverage_95"])],
            "paper/matlab/figures/fig_q1_blind_forecast_interval.m", "168 h 季节朴素基线；与主模型共享盲测样本。",
            [{"variable": "盲测相对小时", "unit": "h"}, {"variable": "系统 GPU 工作量", "unit": "GPU·h"}],
            "18 条序列逐小时求和形成系统曲线；上下界同样逐小时求和且不平滑。冻结覆盖率仍按 432 个底层序列-小时点计算，不等同于系统区间覆盖率。",
            ["24 个系统小时", "432 个底层盲测点", "pooled split-conformal 区间"],
            "24 个小时、每小时 18 条底层序列", "逐小时求和", "名义 95% pooled split-conformal", "经验覆盖率审计",
            ["底层经验覆盖率不是未来概率保证", "汇总上下界不应被解释为单独校准的系统区间"], [main_color, baseline_color, {"role": "observed", "meaning": "实际工作量", "secondary_encoding": "深色圆点实线"}],
        ),
        contract(
            "fig-q1-series-error-pairing", "Q1", "Q1-FCST-TEST-WAPE", "paired-error-dot-plot",
            "同一盲测窗口中 18 条序列的主模型和季节基线 MAE 存在显著异质性。",
            [(q1_series, ["period", "method", "region", "task_type", "mae_gpu_h"])],
            "paper/matlab/figures/fig_q1_series_error_pairing.m", "168 h 季节基线；按区域和任务类型一一配对。",
            [{"variable": "模型", "unit": "类别"}, {"variable": "盲测 MAE", "unit": "GPU·h"}],
            "筛选 blind_test 后，将 shared_hgbr_reconciled 与 seasonal_baseline 按 18 条序列配对；细线只连接同一序列。",
            ["18 条配对序列", "MAE"], "18 条区域-任务类型序列", "24 h MAE", "不适用", "同序列配对复核",
            ["序列 MAE 不等于系统 WAPE", "连接线不是时间轨迹"], [main_color, baseline_color],
        ),
        contract(
            "fig-q1-schedule-gantt", "Q1", "Q1-SCHED-FEASIBLE", "compressed-gantt",
            "538 条实际任务和 carry-in 在六区域中形成可执行、不可抢占的最后 24 h 排程。",
            [(q1_schedule, ["TaskID", "TaskType", "ExecutionRegion", "StartMinute", "EndMinute", "SchedulePhase", "GPU_Demand"]), (q1_audit, ["main.passed", "main.scheduled_final_task_count", "carry_in_count"]), (q1_sched_metrics, ["final_task_count", "carry_in_count", "main.solver.status"])],
            "paper/matlab/figures/fig_q1_schedule_gantt.m", "同约束 FIFO 基线不叠加；可行性由独立 constraint audit 判定。",
            [{"variable": "最后调度日相对小时", "unit": "h"}, {"variable": "执行区域", "unit": "类别"}],
            "任务区间按执行区域压缩，颜色与线型图例区分任务类型，菱形图例标明 carry-in 起点；不显示任务名以避免遮挡。",
            ["538 条正式任务", "58 条 carry-in", "六区域"], "596 条排程记录", "不可抢占区间", "2376--2400 h 显示窗口", "独立硬约束审计",
            ["可行不等于全局最优", "线宽编码 GPU 需求但不用于精确读数"], [main_color, baseline_color, {"role": "carry_in", "meaning": "历史延续任务", "secondary_encoding": "菱形起点"}], "external-legend", 112.0,
        ),
        contract(
            "fig-q1-resource-headroom", "Q1", "Q1-SCHED-FEASIBLE", "resource-headroom-heatmap",
            "Q1 排程在 GPU、IT 与设施功率约束下保持非负余量，但局部时段裕度较窄。",
            [(q1_resource, ["Hour", "Region", "GPU_margin", "GPU_capacity", "IT_margin_MW", "IT_capacity_MW", "Facility_margin_MW", "Facility_capacity_MW", "Schedule"]), (q1_audit, ["main.passed", "main.checks"])],
            "paper/matlab/figures/fig_q1_resource_headroom.m", "容量上限为零余量基准；不与 FIFO 混合。",
            [{"variable": "最后调度日相对小时", "unit": "h"}, {"variable": "区域与资源", "unit": "类别"}],
            "将 GPU、IT 功率和设施功率余量分别除以对应容量并转为百分比；色条承担图例作用。",
            ["6 区域×3 资源×24 小时", "相对容量余量"], "432 个区域-资源-小时单元", "余量/容量", "不适用", "资源上限审计",
            ["低余量不是违规", "三类资源单位不同，仅比较归一化余量"], [{"role": "headroom", "meaning": "相对容量余量", "secondary_encoding": "0--100% 色条刻度"}], "external-legend",
        ),
        contract(
            "fig-q2-load-migration", "Q2", "Q2-FULL-COST-CHANGE-PCT", "signed-migration-heatmap",
            "候选相对 FIFO 的设施负荷迁移具有明确的区域和周内时段结构。",
            [(q2_profiles, ["Method", "Hour", "Region", "Facility_Load_MW"])],
            "paper/matlab/figures/fig_q2_load_migration.m", "同输入同约束 FIFO。",
            [{"variable": "周内小时", "unit": "h"}, {"variable": "执行区域", "unit": "类别"}],
            "按区域与周内小时计算候选减 FIFO 的设施负荷平均差，发散色条以零为中心；正值为迁入，负值为迁出。",
            ["6 区域", "168 个周内小时", "候选减 FIFO"], "6×168 个周内聚合单元", "重复周均值", "不适用", "同输出基线复算",
            ["迁移热图不替代全时域总成本", "区域合计可受任务开始时刻移动影响"], [risk_color, baseline_color], "external-legend",
        ),
        contract(
            "fig-q2-cumulative-impact", "Q2", "Q2-FULL-CARBON-CHANGE-PCT", "cumulative-impact-curves",
            "Q2 的成本和购电碳排改善在全时域逐步形成，最终端点与冻结总量一致。",
            [(q2_profiles, ["Method", "Hour", "ElectricityCost_CNY", "CarbonEmission_tCO2"]), (q2_summary, ["comparison_vs_fifo.cost_change_pct", "comparison_vs_fifo.carbon_change_pct"])],
            "paper/matlab/figures/fig_q2_cumulative_impact.m", "同输入同约束 FIFO。",
            [{"variable": "累计运行时间", "unit": "day"}, {"variable": "相对 FIFO 累计差", "unit": "%"}],
            "按小时汇总六区域成本和碳排，分别累加后除以 FIFO 同期累计量；曲线未平滑，图例置于数据区外。",
            ["2407 个小时", "六区域汇总", "累计百分比差"], "2407 个系统小时", "逐时累计量", "不适用", "终点与冻结摘要核对",
            ["局部上升不代表最终恶化", "成本与碳排共用百分比轴但物理单位不同"], [main_color, baseline_color],
        ),
        contract(
            "fig-q2-latency-ecdf", "Q2", "Q2-FULL-LATENCY-CHANGE-MS", "latency-ecdf",
            "候选排程的任务时延分布相对 FIFO 右移，但逐任务 SLA 审计仍为零违约。",
            [(q2_fifo, ["TaskID", "NetworkLatency_ms"]), (q2_main, ["TaskID", "NetworkLatency_ms"]), (q2_summary, ["feasibility.candidate_sla_violation_rate", "comparison_vs_fifo.latency_change_ms"])],
            "paper/matlab/figures/fig_q2_latency_ecdf.m", "同输入同约束 FIFO。",
            [{"variable": "网络时延", "unit": "ms"}, {"variable": "经验累计概率", "unit": "ratio"}],
            "对两套完整排程的 50000 条任务时延分别排序并计算 ECDF；图例放在右下空白区。",
            ["50000 条任务/方案", "ECDF"], "两套各 50000 条任务", "经验分布", "不适用", "逐任务 MaxLatency 审计",
            ["平均时延增加不等于 SLA 违规", "ECDF 不显示任务各自不同的 SLA 上限"], [main_color, baseline_color],
        ),
        contract(
            "fig-q3-dispatch-soc", "Q3", "Q3-ROLLING-COST-DELTA", "dispatch-and-soc",
            "观测 72 h 中，六区域储能功率流与聚合 SOC 的联动关系可直接复核。",
            [(q3_dispatch, ["Hour", "Region", "ChargePower_MW", "DischargePower_MW", "SOC_MWh", "NetGridImport_MW", "Evaluation", "Scenario", "WindowStart_h"])],
            "paper/matlab/figures/fig_q3_dispatch_soc.m", "同负荷无储能基线用于经济比较，本图展示滚动二进制 MILP 候选。",
            [{"variable": "观测窗口小时", "unit": "h"}, {"variable": "功率", "unit": "MW"}, {"variable": "聚合 SOC", "unit": "MWh"}],
            "筛选 fixed、observed、WindowStart=0 且 Hour<72，按小时汇总六区域功率和 SOC；充放电采用相反线型并共享图例。",
            ["72 小时", "六区域汇总", "充电/放电/净购电/SOC"], "72 个系统小时", "六区域逐小时求和", "不适用", "SOC 与互斥审计",
            ["聚合 SOC 不代表任一区域 SOC", "负净购电表示净外送而非负负荷"], [main_color, risk_color, {"role": "discharge", "meaning": "放电", "secondary_encoding": "点划线"}], "external-legend", 112.0,
            panels=[{"panel": "a", "role": "功率流", "subclaim": "充放电与净电网交换的逐时关系"}, {"panel": "b", "role": "状态量", "subclaim": "聚合 SOC 的逐时演化"}],
            multipanel="储能功率决策与 SOC 状态由同一动力学约束连接，拆分后会破坏对充放电作用的解释。",
        ),
        contract(
            "fig-q3-rolling-runtime-coverage", "Q3", "Q3-ALL-270-AUDITS-PASS", "rolling-runtime-heatmap",
            "六区域 90 个滚动二进制 MILP 块均成功求解，修复后的完整硬约束审计为 270/270。",
            [(q3_windows, ["evaluation", "scenario", "window_start_h", "region", "runtime_s_candidate"]), (q3_audit, ["audit_boundary.total_audits_passed", "audit_boundary.total_audit_count"])],
            "paper/matlab/figures/fig_q3_rolling_runtime_coverage.m", "无储能同口径基线同时通过对应审计；本图不比较经济指标。",
            [{"variable": "滚动窗口起点", "unit": "day"}, {"variable": "区域", "unit": "类别"}],
            "筛选 observed 的 90 个 rolling_block 记录，绘制区域×窗口运行时间热图；右下空白区直接标注修复后的 270/270 审计。",
            ["6 区域×15 块", "90 次求解", "270/270 审计"], "90 个滚动二进制 MILP 块", "单块运行时间", "不适用", "区域独立全周期二进制探针与确定性复跑",
            ["270/270 不证明系统级全时域全局最优", "六个全周期探针按区域独立求解"], [{"role": "runtime", "meaning": "MILP 运行时间", "secondary_encoding": "秒单位色条"}], "external-legend",
        ),
        contract(
            "fig-q4-scenario-tradeoff", "Q4", "Q4-LOWREN-CARBON-DELTA", "scenario-tradeoff-scatter",
            "五场景中局部联合候选相对顺序基线形成可解释的成本、碳排和新能源利用权衡。",
            [(q4_metrics, ["scenario", "role", "cost_CNY", "carbon_tCO2", "renewable_utilization_ratio"]), (q4_summary, ["audit.all_hard_constraints_passed", "low_renewable_72h", "joint_stress_72h"])],
            "paper/matlab/figures/fig_q4_scenario_tradeoff.m", "固定 Q2 排程加六区域储能 recourse 的顺序基线。",
            [{"variable": "净运行成本", "unit": "10^6 CNY"}, {"variable": "购电侧碳排", "unit": "tCO2"}],
            "每个场景连接顺序基线与局部联合候选，候选点面积编码新能源利用率增益；完全重合场景合并标签且不抖动。",
            ["5 个场景×2 方案", "成本-碳排散点", "点面积编码新能源利用率增益"], "10 个场景-方案单元", "场景级总量", "不适用", "硬约束与确定性复跑",
            ["重合点不代表场景输入完全相同", "点面积只编码增益方向和相对大小"], [main_color, baseline_color],
        ),
        contract(
            "fig-q4-system-profile", "Q4", "Q4-OBS-COST-DELTA", "system-profile-difference",
            "观测 72 h 中，局部联合候选相对顺序基线只在少数关键小时改变 AI 负荷与净电网交换。",
            [(q4_main, ["Hour", "AI_IT_Load_MW", "NetGridImport_MW"]), (q4_base, ["Hour", "AI_IT_Load_MW", "NetGridImport_MW"]), (q4_summary, ["scope", "observed_72h.cost_delta_CNY"])],
            "paper/matlab/figures/fig_q4_system_profile.m", "观测场景顺序基线。",
            [{"variable": "观测窗口小时", "unit": "h"}, {"variable": "候选减基线", "unit": "MW"}],
            "两套 dispatch 按小时汇总六区域 AI IT 负荷和净电网交换，再作候选减基线；阶梯线配合采样标记，图例置于数据区外。",
            ["72 小时", "六区域汇总", "候选减顺序基线"], "72 个系统小时", "六区域逐小时求和后作差", "不适用", "任务、储能与电网硬约束审计",
            ["曲线差为局部联合效果而非因果效应", "72 h 结果不能外推为全时域全局最优"], [main_color, risk_color],
        ),
    ]

    payload = {
        "schema_version": 2,
        "status": "governed",
        "palette_id": "journal-spectrum-v2",
        "formal_source": "paper/matlab/build_all_figures.m",
        "figure_count": len(figures),
        "figures": figures,
    }
    output = ROOT / "paper/figure_contracts.yaml"
    output.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
