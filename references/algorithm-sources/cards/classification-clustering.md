---
algorithm_card_id: classification-clustering
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "04_分类与聚类"
entry_points:
  - path: "04_分类与聚类/01_KMeans聚类.py"
    symbol: "kmeans_cluster"
    kind: function
    purpose: "按特征相似性划分样本并输出簇标签"
    input: "数值特征矩阵、簇数"
    output: "簇标签和簇中心"
    file_sha256: "c762d66d4aed59122145378f5117d7d5c9304545e8eefb422a1f8f4f957747d5"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/04_%E5%88%86%E7%B1%BB%E4%B8%8E%E8%81%9A%E7%B1%BB/01_KMeans%E8%81%9A%E7%B1%BB.py"
  - path: "04_分类与聚类/05_逻辑回归分类.py"
    symbol: "run_logistic"
    kind: function
    purpose: "监督分类并输出测试集分类指标"
    input: "特征矩阵、标签和正则化参数"
    output: "预测标签和分类评价指标"
    file_sha256: "3993fb04463c464655085975bd29622e20431f38f5756b52ce54ee325149ef71"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/04_%E5%88%86%E7%B1%BB%E4%B8%8E%E8%81%9A%E7%B1%BB/05_%E9%80%BB%E8%BE%91%E5%9B%9E%E5%BD%92%E5%88%86%E7%B1%BB.py"
skeleton_path: "references/algorithm-sources/skeletons/classification/classification_contract.py"
tags: [classification, clustering, kmeans, dbscan, svm, random-forest, supervised, unsupervised]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "feature matrix plus labels or no labels -> clusters or out-of-sample class predictions"
baseline_required: [majority-class, standardized-kmeans, simple-threshold]
baseline_options:
  - {id: majority-class, when: "监督分类且类别不平衡需有可比基线", required: true}
  - {id: standardized-kmeans, when: "无标签聚类", required: true}
  - {id: blocked-or-stratified-split, when: "存在时间、空间或群组结构", required: true}
known_risks: ["标准化和类别编码必须只在训练折拟合", "KMeans的簇数不能只凭默认值", "无标签聚类指标不等于业务有效性", "类别不平衡时accuracy可能误导"]
adaptation_required: ["定义标签和特征角色", "选择分层/分组/时间切分", "记录K或密度参数依据", "报告混淆矩阵或簇稳定性"]
---

## 适用信号

题面要求用户分群、状态识别、风险分类或样本画像时使用。先判断是否有可靠标签；无标签时进入聚类，不要把聚类结果直接称为类别真值。

## 输入输出

输入是经过单位、缺失、异常和泄漏检查的特征矩阵，监督任务还需要标签定义。输出必须包含样本级标签、训练/验证规则和可解释的类别或簇画像。

## baseline 与升级

监督分类先用多数类、简单阈值或逻辑回归；聚类先用标准化 KMeans，再比较 DBSCAN、层次聚类或 GMM。只有在外部验证、稳定性和解释性有收益时升级。

## 验证要求

分类报告分层或分组样本外指标、混淆矩阵、类别不平衡处理和阈值规则。聚类报告轮廓系数、簇稳定性、簇画像及业务解释，不能只报告一张散点图。

## 已知风险

随机切分会泄漏同一对象、时间段或空间单元；特征缩放、类别编码和缺失填补必须在训练折内拟合。无标签聚类的内部指标不能替代题面意义验证。

## 停止与回退

若复杂分类器不能稳定超过简单基线，回退到可解释模型；若聚类对初始化、K或参数极敏感，缩小结论为探索性分组。

## 适配步骤

先填写特征/标签 schema，再确定切分、预处理、模型和指标，最后将簇或类别结果交给 visualization-design 设计图表。

## 来源与边界

参考固定 commit 的 [04_分类与聚类](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/04_%E5%88%86%E7%B1%BB%E4%B8%8E%E8%81%9A%E7%B1%BB)。源无明确许可证，只读学习；不得执行或直接复制代码。
