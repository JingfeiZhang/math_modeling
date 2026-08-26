---
algorithm_card_id: preprocess-visualization
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "01_数据预处理与可视化"
entry_points:
  - path: "01_数据预处理与可视化/01_缺失值与异常值处理.py"
    symbol: "detect_missing"
    kind: function
    purpose: "生成字段缺失概览"
    input: "pandas DataFrame"
    output: "缺失统计表"
    file_sha256: "3f311b73da5ae7ca48bac91df671fbf5724db10b2ce63b873318daadf18c1b3a"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/01_%E6%95%B0%E6%8D%AE%E9%A2%84%E5%A4%84%E7%90%86%E4%B8%8E%E5%8F%AF%E8%A7%86%E5%8C%96/01_%E7%BC%BA%E5%A4%B1%E5%80%BC%E4%B8%8E%E5%BC%82%E5%B8%B8%E5%80%BC%E5%A4%84%E7%90%86.py"
skeleton_path: "references/algorithm-sources/skeletons/preprocess/preprocess_contract.py"
tags: [preprocess, visualization, missing-data, outlier, correlation]
stage_scope: [P1, P2, P3a]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "pandas DataFrame -> cleaned DataFrame and exploratory figures"
baseline_required: [raw-summary, missingness-table, unit-check]
baseline_options:
  - {id: raw-summary, when: "所有数据题", required: true}
  - {id: missingness-table, when: "存在缺失字段", required: true}
  - {id: unit-check, when: "字段含量纲或时间粒度", required: true}
known_risks: ["示例数据不是真实附件", "异常值规则必须由题面和业务含义决定", "图表配色与正式 Figure Contract 不一致"]
adaptation_required: ["字段和单位账本", "缺失机制说明", "按题目目的选择图型", "保存只读变换记录"]
---

## 适用信号

拿到 CSV/Excel 后，需要快速查看字段类型、缺失、异常、量纲、时间排序、相关性或分布形态时使用。它是 P1 数据审查入口，不是自动清洗器。

## 输入输出

输入应是当前项目复制并哈希登记的数据文件。输出应包括字段清单、缺失/异常报告、单位说明和可复核的清洗变换；绘图只能消费当前项目数据。

## baseline 与升级

先做行列数、字段类型、缺失率、重复行和单位检查，再考虑插补、变换、降维或异常值处理。升级必须说明删除、截尾、插补或标准化对主指标的影响。

## 验证要求

检查清洗前后行数、关键总量、时间顺序和约束范围；随机抽查原始行与变换后行。绘图前先完成 visual intent，避免为图而图。

## 已知风险

仓库中的示例图和示例统计不能进入论文。相关性不等于因果，异常点不能仅凭箱线图删除，时间序列不能随机打乱。

## 停止与回退

若清洗规则改变题面主指标或无法解释，停止升级，保留原始数据和最小可运行 baseline，回退到只报告数据质量问题。

## 适配步骤

依据算法思路自行重写等价流程，替换字段名和单位；为每个变换记录输入字段、输出字段、规则、代码哈希和影响范围。正式图件另走 visualization-design 链。

## 来源与边界

参考 [01_数据预处理与可视化](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/01_%E6%95%B0%E6%8D%AE%E9%A2%84%E5%A4%84%E7%90%86%E4%B8%8E%E5%8F%AF%E8%A7%86%E5%8C%96)。该源无明确许可证，只读学习，不直接复制或再发布。
