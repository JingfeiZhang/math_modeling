---
algorithm_card_id: statistics-inference
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "07_统计分析"
entry_points:
  - path: "07_统计分析/03_方差分析ANOVA.py"
    symbol: "one_way_anova_df"
    kind: function
    purpose: "按分组因子检验均值差异并提供事后比较入口"
    input: "长表、响应变量列和分组列"
    output: "ANOVA统计量、p值和效应量记录"
    file_sha256: "e99788f5e9b4ca60ef27772037c93c8f854d21eadfe1f8fdc1c7edad8fe97549"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/07_%E7%BB%9F%E8%AE%A1%E5%88%86%E6%9E%90/03_%E6%96%B9%E5%B7%AE%E5%88%86%E6%9E%90ANOVA.py"
skeleton_path: "references/algorithm-sources/skeletons/statistics/inference_contract.py"
tags: [statistics, hypothesis-testing, anova, correlation, pca, bayesian, design-of-experiments]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "grouped observations and hypotheses -> statistical tests, effect sizes and uncertainty"
baseline_required: [descriptive-summary, permutation-or-bootstrap, nonparametric-check]
baseline_options:
  - {id: descriptive-summary, when: "所有统计题", required: true}
  - {id: assumption-check, when: "使用参数检验前", required: true}
  - {id: permutation-or-bootstrap, when: "小样本或分布假设不稳", required: true}
known_risks: ["p值不等于效应大小", "多重比较会膨胀第一类错误", "重复测量不能当作独立样本", "正态性检验不能替代设计判断"]
adaptation_required: ["定义零假设和分析单位", "锁定alpha和多重比较规则", "报告效应量与区间", "按组/时间/空间结构选择检验"]
---

## 适用信号

题面要求比较组间差异、识别显著因素、分析相关关系、降维或估计不确定性时使用。统计检验必须服务于题面问题，不把显著性检验当作因果证明。

## 输入输出

输入应明确观测单位、分组因子、响应变量、重复结构和缺失处理。输出至少包含假设、统计量、p值、效应量、置信区间、假设检查和多重比较处理。

## baseline 与升级

先做描述统计、可视化和简单差异/相关基线；再按设计选择ANOVA、非参数检验、置换检验、Bootstrap、回归或层级模型。

## 验证要求

检查独立性、分布、方差和重复测量结构；报告效应量而非只报告 p 值。小样本、偏态或异方差时给出稳健/非参数敏感性结果。

## 已知风险

多次试验、事后挑选指标、忽略分组和把相关写成因果都会夸大结论。统计阈值和示例数据不能直接迁移到比赛题面。

## 停止与回退

若设计假设不满足，改用稳健或非参数方法并收窄解释；若结果只在单一阈值下成立，报告敏感性而不是绝对结论。

## 适配步骤

先写统计问题和分析单位，再确定检验/估计方法、基线、效应量和敏感性方案；所有数字由当前项目实验生成。

## 来源与边界

参考固定 commit 的 [07_统计分析](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/07_%E7%BB%9F%E8%AE%A1%E5%88%86%E6%9E%90)。源无明确许可证，只读学习；不得执行或直接复制代码。
