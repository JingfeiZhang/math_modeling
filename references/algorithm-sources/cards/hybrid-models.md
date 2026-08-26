---
algorithm_card_id: hybrid-models
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "11_组合模型（创新加分）"
entry_points:
  - path: "11_组合模型（创新加分）/01_灰色Markov预测.py"
    symbol: "grey_markov"
    kind: function
    purpose: "将灰色预测与状态转移修正组合"
    input: "短序列、预测步数和状态划分规则"
    output: "组合预测、状态序列和误差指标"
    file_sha256: "e2bdcc597bfa838b0c40989d18fda22b2b647cec8f8921059dd106248a2f0dd1"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/11_%E7%BB%84%E5%90%88%E6%A8%A1%E5%9E%8B%EF%BC%88%E5%88%9B%E6%96%B0%E5%8A%A0%E5%88%86%EF%BC%89/01_%E7%81%B0%E8%89%B2Markov%E9%A2%84%E6%B5%8B.py"
  - path: "11_组合模型（创新加分）/02_GA_SA组合优化.py"
    symbol: "ga_sa_optimize"
    kind: function
    purpose: "将全局探索与局部搜索组合用于候选优化"
    input: "目标函数、边界和随机种子"
    output: "候选解、目标轨迹和多种子统计"
    file_sha256: "ab5e374a489b48096b49b7d3a348a0a249d29be4d5eea8230c5c0c5aa89b5fb6"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/11_%E7%BB%84%E5%90%88%E6%A8%A1%E5%9E%8B%EF%BC%88%E5%88%9B%E6%96%B0%E5%8A%A0%E5%88%86%EF%BC%89/02_GA_SA%E7%BB%84%E5%90%88%E4%BC%98%E5%8C%96.py"
skeleton_path: "references/algorithm-sources/skeletons/combination/hybrid_contract.py"
tags: [hybrid, combination, grey-markov, predict-then-optimize, ensemble, ga-sa]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "component models with an explicit interface -> hybrid output and ablation comparison"
baseline_required: [component-a, component-b, no-hybrid]
baseline_options:
  - {id: component-a, when: "组合模型的第一个组成模型", required: true}
  - {id: component-b, when: "组合模型的第二个组成模型", required: true}
  - {id: no-hybrid, when: "所有组合模型", required: true}
known_risks: ["组合不能以复杂为创新理由", "接口和信息流必须明确", "组件增益需用消融实验证明", "随机组合搜索必须保留种子和轨迹"]
adaptation_required: ["定义组件输入输出", "设计消融和公平基线", "锁定组合参数来源", "限制结论范围"]
---

## 适用信号

只有当题面存在明确的两阶段或多阶段接口，且单一模型存在可解释缺口时才考虑组合模型。组合不是默认升级方向。

## 输入输出

必须记录组件模型、数据流、接口变量、训练顺序、参数来源和最终输出。组合模型与各组件必须产生同类别输出，才能进行公平比较。

## baseline 与升级

分别运行组件 A、组件 B 和不组合方案，再做组合；若组合没有稳定增益或增益无法解释，退回简单模型。

## 验证要求

至少提供消融、样本外/场景验证、参数敏感性和随机种子记录。预测组合报告滚动验证，优化组合报告可行性和轨迹。

## 已知风险

组件间数据泄漏、重复使用验证集、接口单位不一致和只展示最优一次结果会夸大组合优势。

## 停止与回退

若组合增益低于复杂度成本，保留组件中更可解释者；若无法完成消融和公平基线，不进入 Formal。

## 适配步骤

先画组件接口，再确定基线、消融和验证合同；组合结果仍只能使用当前项目自己的运行证据。

## 来源与边界

参考固定 commit 的 [11_组合模型](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/11_%E7%BB%84%E5%90%88%E6%A8%A1%E5%9E%8B%EF%BC%88%E5%88%9B%E6%96%B0%E5%8A%A0%E5%88%86%EF%BC%89)。源无明确许可证，只读学习；不得执行或直接复制代码。
