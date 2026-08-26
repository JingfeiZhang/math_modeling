---
algorithm_card_id: evaluation-ranking
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "02_评价类模型"
entry_points:
  - path: "02_评价类模型/01_TOPSIS法.py"
    symbol: "topsis"
    kind: function
    purpose: "按指标方向和权重计算方案贴近度排序"
    input: "决策矩阵、指标方向、可选权重"
    output: "方案得分和排序"
    file_sha256: "90baa1d1962e31c391a1b3a54842307591d175d3e3aa6c9b19899fb912a8c700"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/02_%E8%AF%84%E4%BB%B7%E7%B1%BB%E6%A8%A1%E5%9E%8B/01_TOPSIS%E6%B3%95.py"
skeleton_path: "references/algorithm-sources/skeletons/evaluation/ranking_contract.py"
tags: [evaluation, ranking, topsis, entropy-weight, ahp, dea]
stage_scope: [P1, P2, P3a]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "decision matrix + indicator directions -> scores, weights and ranking"
baseline_required: [equal-weight-score, simple-normalized-ranking]
baseline_options:
  - {id: equal-weight-score, when: "没有可靠外部权重", required: true}
  - {id: simple-normalized-ranking, when: "需要可解释排序对照", required: true}
  - {id: weight-sensitivity, when: "结论依赖指标权重", required: true}
known_risks: ["指标正负方向可能写反", "熵权受样本分布影响", "AHP 权重依赖主观判断", "排序稳定性未证明"]
adaptation_required: ["指标方向和单位合同", "权重扰动", "删项稳定性", "与简单排序 baseline 比较"]
---

## 适用信号

题目要求对多个对象、方案或地区进行综合评价、排序、分级或优先级分配时使用。若题面实际要求优化决策，不要用评价模型替代优化模型。

## 输入输出

输入是对象-指标矩阵，必须记录每个指标的方向、单位、缺失处理和观测时间。输出是分数、排名、权重和排序稳定性，而不是未经解释的“综合指数”。

## baseline 与升级

先做等权标准化加权和或单指标排序作为 baseline，再考虑 TOPSIS、熵权、AHP、DEA 或 VIKOR。升级只能由指标尺度、权重来源或决策偏好驱动。

## 验证要求

至少做指标方向回查、权重扰动、删项重排和简单 baseline 对照。若排名发生大幅变化，结论必须写成条件性排序。

## 已知风险

多种赋权方法同时使用不等于模型更可靠。不能把排序结果解释为因果效应，也不能把权重稳定性当作预测准确性。

## 停止与回退

若权重没有题面或领域依据，或不同合理权重导致排名冲突，回退到多方案并列比较，不强行给出唯一排名。

## 适配步骤

把指标方向、标准化公式、权重来源和输出单位写入指标合同；将算法函数接入项目 runner，输出每个对象的中间量和最终排序，并固定随机性（若有）。

## 来源与边界

参考 [02_评价类模型](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/02_%E8%AF%84%E4%BB%B7%E7%B1%BB%E6%A8%A1%E5%9E%8B)。该源无明确许可证，只读学习，不直接复制或再发布。
