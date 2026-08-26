# 算法路由与模型选择学术质量手册

目标不是自动选算法，而是让候选方法与数学结构、数据条件、验证能力和论文解释一致。

## 1. 统一路由原则

每问默认 `Baseline → Main → Challenger → Fallback`。升级必须由已观察到的失败点触发。

## 2. 预测 / 回归

Baseline：mean/median、persistence/seasonal naive、simple linear/regularized regression。

主模型：趋势/季节 → ETS/ARIMA/STL；外生变量 → dynamic regression/GAM；多特征非线性 → tree ensemble/boosting；多序列动态 → VAR/状态空间；数据充分且复杂长依赖有证据 → 深度时序。

升级条件：残差存在稳定结构、非线性、外生驱动或长期依赖，并在多个时间窗口稳定改善。

## 3. 分类

`prevalence/simple rule → logistic → tree/SVM/boosting → calibration/ensemble（有必要时）`。类别不平衡时 PR 和代价驱动阈值优先。

## 4. 评价 / 排序

`equal-weight baseline → justified weighting → TOPSIS/VIKOR/DEA/其他结构匹配评价 → weight/rank stability`。AHP、熵权、TOPSIS 不是必须组合链。

## 5. 聚类

`scale/distance check → KMeans/simple partition → hierarchical/GMM → DBSCAN/HDBSCAN（有密度/噪声依据）`。除 silhouette 还看扰动稳定性和簇解释。

## 6. 优化

`rule/greedy → LP → MILP/QP → NLP → network/DP/decomposition → heuristic/metaheuristic`。能精确建模时不优先元启发式。

## 7. 多目标

少量可解释目标用 weighted sweep / epsilon constraint；非凸/大规模前沿可考虑 NSGA-II；推荐点用 knee/边际交换/现实偏好。固定一个权重不能宣称完整 Pareto。

## 8. 机理 / 动力学

先最简机制/守恒，再依据拟合失败增加状态或反馈。参数可辨识性比方程数量重要。

## 9. 图论 / 网络 / 调度

先构图再选算法：非负最短路 Dijkstra；全源 APSP；连接成本 MST；容量 flow；成本+容量 min-cost flow；时窗/多资源/逻辑用 MILP、time-expanded network 或 scheduling。

## 10. 仿真

先定义状态、事件、随机源、预热期、重复次数和输出，再做 scenario/factor design。仿真不是万能验证。

## 11. 统计推断

依据独立/配对、组数、变量尺度、依赖结构、效应量与区间需求选方法，不把正态检验当万能路由器。

## 12. 因果与解释

观察性数据默认只支持关联/预测。只有研究设计和识别假设充分时才使用因果方法和措辞。

## 13. 模型竞争公平性

统一输入信息、输出定义、数据切分、评价指标、约束和调参预算。不能用不公平预算制造主模型胜出。

## 14. 保留复杂模型的理由

改善需跨切分/场景稳定、量级有实际意义、修复已识别失败、未明显恶化可行性/稳定性，并能解释其作用，否则回退。
