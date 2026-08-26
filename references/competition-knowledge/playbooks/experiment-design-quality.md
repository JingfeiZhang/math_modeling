# 实验设计与证据质量手册

实验不是证明模型很好，而是区分候选解释、攻击关键假设并确定 claim 边界。

## 1. 优先级

`正确性 → baseline 增益 → 最可能失败点 → 不确定性/稳健性 → 机制解释 → 精细调参`。

## 2. 默认最小组合

每问通常只需 baseline comparison + 一项题型专项验证 + 一项现实有意义的 robustness/uncertainty + 一项 failure-case。不是所有题都需要 ablation、多种子、灵敏度或交叉验证。

## 3. Known-answer / invariant

优先构造人工可算小实例、穷举、解析极限、守恒/容量不变量、单调性/边界行为，先验证实现正确性。

## 4. Baseline comparison

保证输入信息、切分、指标和约束公平；报告绝对值与相对变化，避免只写提升百分比。

## 5. Challenger

测试一个真正不同的解释，如线性 vs 非线性、deterministic vs robust、statistical vs tree。不要堆高度相似模型。

## 6. Ablation

只有模型由可分离组件组成且声称组件有贡献时做。Full 不稳定优于各组件时不能把所有组件都写创新。

## 7. 超参数

合理默认跑通 → 粗搜索 → 只细调敏感参数。模型价值未确认前禁止大规模搜索。

## 8. 时间序列

rolling/expanding、out-of-time、horizon 分层、peak/extreme、interval coverage。所有 tuning 在训练窗口内。

## 9. 分类

stratified/group/time split、PR/ROC（按不平衡程度）、threshold-cost、confusion、calibration、subgroup performance。

## 10. 排序/评价

equal-weight baseline、权重扰动、指标删除、top-k stability、极端方案敏感性。

## 11. 优化

constraint audit、solver status/gap、small exact case/lower bound、stress scenario、resource bottleneck、关键成本/需求参数敏感性。

## 12. 元启发式

统一 function-evaluation budget、多 seed、feasibility、精确/松弛/简单 reference，报告分布而非最好一次。

## 13. 机理

dimension、boundary/initial condition、conservation、limit case、calibration vs validation、parameter sensitivity/identifiability。

## 14. 场景与稳健性

场景有现实含义，优先题面、历史分布、文献范围或可解释压力区间，不默认高斯噪声。区分 data/parameter/scenario/model/algorithm uncertainty。

## 15. Failure case

主动找最差时间段、最弱群体、最紧约束、参数边界、误差传播最严重场景。失败分析用于确定适用范围。

## 16. 停止规则

主模型相对 baseline 结论稳定、最关键风险已测试、Challenger 不改主结论、新实验不会改变模型选择或 claim 时停止。

## 17. 实验到论文

每项正式实验明确：研究问题 → 对比/扰动 → 评价指标 → 结果 → 对模型判断的影响。不能只写做了敏感性分析。
