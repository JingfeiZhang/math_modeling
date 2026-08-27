# 10 模型验证与诊断

> 本目录提供误差、灵敏度、稳健性、交叉验证和残差诊断工具。**没有任何规则要求每个模型固定完成“误差 + 灵敏度 + 稳健性三件套”。** 高质量验证应针对当前模型最可能失败的环节。

## 验证从失败风险开始

先写：

```text
如果这个模型是错的，最可能错在哪里？
```

然后再选检验。

## 方法选择

| 模型/任务 | 首要风险 | 优先验证 |
|---|---|---|
| 时间预测 | 泄漏、峰值误差 | rolling/out-of-time、group error、interval coverage |
| 回归 | 结构错配、异方差 | holdout、residual、robust alternative |
| 分类 | 不平衡、阈值 | PR、confusion、threshold、calibration |
| 排序评价 | 权重任意性 | weight/rank stability、删指标 |
| 优化 | 不可行、近似质量 | feasibility、small exact case/gap、stress scenario |
| 启发式 | 随机波动 | multi-seed、reference、trajectory |
| 机理 | 边界/参数错误 | dimension、conservation、limit、sensitivity |
| 聚类 | 伪结构 | perturbation stability、interpretability |

## 误差分析

只适用于存在真实目标和可比较预测/拟合输出的任务。指标必须与题面一致；训练拟合误差不能替代样本外预测证据。

## 灵敏度分析

只针对真正重要且不确定的参数。扰动范围必须有业务、题面或数据依据；机械 ±10/20/30% 只能作为探索，不应自动成为正式结论。

## 稳健性

“加高斯噪声”不是所有任务的通用稳健性。优先构造现实可解释的场景：需求冲击、价格变化、权重变化、边界变化、样本扰动等。

## 交叉验证

切分必须与数据结构一致。时间序列不用随机 K 折；同一主体多次观测需要 group split；空间问题必要时使用 spatial blocking。

## 残差诊断

正态性不是所有模型的强制要求。只有当推断、区间或模型假设依赖残差结构时，才需要相应检验。

## 论文表达

只保留最能增强主结论可信度的 1–3 项验证。每项写：验证什么风险、如何做、结果如何、是否改变结论。不要用“模型通过检验”这种无信息措辞。
