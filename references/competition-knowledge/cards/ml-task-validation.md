---
card_id: ml-task-validation
tags: [machine-learning, task-selection, validation, baseline, metrics]
source_id: li-hang-machine-learning
source_sha256: FFA1264B286689587F5A30AE1183BD140D8D0916FC1A7C068F0C9C306E01538F
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 任务与模型评估
section: 任务匹配、指标与验证
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 任务与模型评估

## 适用信号
题目要求预测、分类、聚类或降维且输入输出明确

## 必要前提
区分监督/无监督、回归/分类和预测时点，指标对应题目代价

## 最小建模骨架
定义训练对象、标签和损失，建立预处理-模型-评估管道

## 算法/代码入口
从 Dummy、线性、树和集成开始，按时间/组切分

## 同输出 baseline
DummyRegressor/Classifier、均值、持久性或简单规则

## 验证与敏感性
按任务报告 MAE/RMSE/F1等，做阈值敏感性和校准

## 停止条件
标签不可靠或指标不可解释时先修正接口

## 误用风险
不平衡只报准确率、聚类标签当真值、破坏时序切分

## 原书回退定位
回看 machine-learning 的学习任务、性能度量和模型选择章节。当前页码仅作章节级定位，精确页码和公式使用前必须人工对照 PDF。

## 决策判断
先锁定“预测时点、决策对象和损失代价”，再选任务类型：连续目标用回归，离散标签用分类，无标签分组只能作为探索，不能把聚类编号当真值。若题目更关心极端误差、排序或概率风险，指标应与该代价一致，RMSE、F1 或 AUC 不能互相替代。

## 关键量与诊断
回归至少记录 MAE、RMSE 和相对/分位误差；分类记录混淆矩阵、宏平均 F1、平衡准确率和概率校准；时间序列使用滚动起点而非随机打乱。任何预处理、特征选择和阈值都必须在训练折内拟合。诊断需包含按组/时间切片的误差，防止总体指标掩盖关键子群失败。

## 赛中最小试验
先运行题目认可的最简单规则或 Dummy baseline，再运行一个可解释模型和一个候选复杂模型；使用同一切分、同一指标和同一输出格式。若标签定义、评估时点或观测单位仍有歧义，先修正接口，不进入调参或模型排名。
