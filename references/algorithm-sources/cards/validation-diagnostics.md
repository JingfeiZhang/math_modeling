---
algorithm_card_id: validation-diagnostics
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "10_模型检验"
entry_points:
  - path: "10_模型检验/03_稳健性分析.py"
    symbol: "model_comparison_robustness"
    kind: function
    purpose: "比较多个模型在扰动或重采样下的稳健性"
    input: "数据、模型映射和随机种子"
    output: "模型比较与稳健性统计"
    file_sha256: "8943cd54e3f51a47e941df6ea8b28dc28156b819245d1ccd1bf56d6b6eb3a0ac"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/10_%E6%A8%A1%E5%9E%8B%E6%A3%80%E9%AA%8C/03_%E7%A8%B3%E5%81%A5%E6%80%A7%E5%88%86%E6%9E%90.py"
skeleton_path: "references/algorithm-sources/skeletons/validation/robustness_contract.py"
tags: [validation, diagnostics, cross-validation, sensitivity, robustness, residual]
stage_scope: [P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "model + data + validation design -> metrics, residuals and robustness diagnostics"
baseline_required: [holdout, naive-or-simple-model]
baseline_options:
  - {id: rolling-origin, when: "时间序列或有序观测", required: true}
  - {id: blocked-holdout, when: "有明确时间外留出窗口", required: true}
  - {id: simple-model, when: "比较复杂模型", required: true}
known_risks: ["默认 K 折不适合时间序列", "训练分数不能代替样本外结果", "敏感性范围不能凭空设定", "示例阈值不是通用标准"]
adaptation_required: ["按题型选择切分", "主指标和单位", "参数扰动方案", "最差情形和失败条件"]
---

## 适用信号

任何模型准备从 Candidate 晋升、或需要解释“模型更好、更稳健、更可靠”时使用。验证方法必须与数据生成机制和题面指标匹配。

## 输入输出

输入是当前项目的模型、数据切分和指标合同。输出应包括样本外指标、残差/误差诊断、敏感性、稳健性、最差情形和失败条件。

## baseline 与升级

先做 holdout 和简单模型对照，再增加 K 折、滚动验证、留一法、残差诊断或参数扰动。时间序列优先滚动或时间外验证，分组数据优先按组阻断。

## 验证要求

验证报告必须写明切分规则、随机种子、指标公式、单位、每折/每窗口结果和聚合方式。优化问题增加可行率、gap 或求解状态；随机算法增加多种子。

## 已知风险

训练集高分、随机 K 折或单次随机种子不能证明泛化和稳定性。代码中的示例阈值只能用于演示，不能直接当作比赛标准。

## 停止与回退

若验证设计与数据结构不匹配，先修正切分而不是继续调参；若模型无法稳定超过 baseline，回退并缩小结论范围。

## 适配步骤

把验证设计写入算法证据合同，保存每个窗口/种子的指标和轨迹；将图件设计与数据 manifest 绑定，正式图另走 Figure Contract。

## 来源与边界

参考 [10_模型检验](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/10_%E6%A8%A1%E5%9E%8B%E6%A3%80%E9%AA%8C)。该源无明确许可证，只读学习，不直接复制或再发布。
