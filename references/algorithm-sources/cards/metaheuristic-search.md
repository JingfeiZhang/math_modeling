---
algorithm_card_id: metaheuristic-search
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "06_智能优化算法"
entry_points:
  - path: "06_智能优化算法/06_NSGA2多目标.py"
    symbol: "NSGA2"
    kind: class
    purpose: "维护多目标非支配排序和拥挤距离搜索"
    input: "目标函数、变量边界、种群规模和迭代预算"
    output: "候选解、目标值和迭代轨迹"
    file_sha256: "62f914a1508c926a16475ca54b6a5911e9e2197201c6d637fbbeff536637056c"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/06_%E6%99%BA%E8%83%BD%E4%BC%98%E5%8C%96%E7%AE%97%E6%B3%95/06_NSGA2%E5%A4%9A%E7%9B%AE%E6%A0%87.py"
skeleton_path: "references/algorithm-sources/skeletons/metaheuristic/nsga2_contract.py"
tags: [metaheuristic, ga, pso, sa, aco, de, nsga2, multiobjective]
stage_scope: [P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "bounded objective/evaluator -> candidate solutions and objective traces"
baseline_required: [exact-small-instance, greedy-or-rule]
baseline_options:
  - {id: exact-small-instance, when: "可构造小规模精确实例", required: true}
  - {id: greedy-or-rule, when: "需要全规模可行初解", required: true}
  - {id: multi-seed-trace, when: "声称随机算法稳定或收敛", required: true}
known_risks: ["手写 NSGA-II 未覆盖一般约束", "随机种子和收敛轨迹缺少统一回执", "连续编码不能直接处理整数/离散变量", "启发式结果不证明最优"]
adaptation_required: ["可行性修复或显式惩罚", "至少三个独立种子", "收敛轨迹", "与精确/规则 baseline 比较"]
---

## 适用信号

只有当精确模型在合理时间内不可用、搜索空间非凸且题面确实需要近似搜索时使用。连续边界问题与整数/组合问题必须分别选择编码和修复策略。

## 输入输出

输入是显式定义的决策编码、上下界、目标和约束。输出必须包括候选方案、目标值、可行性、随机种子、迭代预算、停止原因和轨迹。

## baseline 与升级

先做小规模精确解、穷举、贪心或规则方案；再选择 GA/DE/PSO/SA/ACO/NSGA-II。多目标至少输出多个非支配方案，不能用一个固定权重解冒充 Pareto。

## 验证要求

至少三个独立种子，报告最好值、均值、标准差、可行率和收敛轨迹；在小规模实例与精确解或上下界比较，并检查最差情形。

## 已知风险

仓库模板主要是教学实现，不含通用约束处理、最优性证明或完整质量指标。随机结果不能直接写成稳定、最优或全局结论。

## 停止与回退

若多个种子结果差异大、可行率低或没有超过 baseline，回退到精确/规则方法，或把结论降级为有限预算下的近似结果。

## 适配步骤

定义编码和解码函数，加入约束修复或可解释惩罚；记录每代轨迹、种子和运行时间；Formal 时固定环境、代码和输入哈希。

## 来源与边界

参考 [06_智能优化算法](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/06_%E6%99%BA%E8%83%BD%E4%BC%98%E5%8C%96%E7%AE%97%E6%B3%95)。该源无明确许可证，只读学习，不直接复制或再发布。
