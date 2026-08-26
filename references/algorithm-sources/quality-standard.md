# 算法参考层质量标准

本标准约束 `references/algorithm-sources/` 与 `代码库/` 的使用方式。参考算法用于 P1–P3 的候选发现、baseline 设计、假设检查和风险探针；它们不是 Formal Evidence，也不能直接成为论文数字或最终提交代码。

## 1. 正确定位

算法参考层的价值不是“快速找到一个能跑的模型”，而是帮助回答：

- 这种数学结构有哪些合理候选？
- 每个候选需要什么数据和假设？
- 最简单 baseline 是什么？
- 哪个失败风险最值得先测？
- 什么证据才能证明升级值得？

使用路径：

```text
题意与数学结构
→ algorithm card
→ 必要时阅读代码示例
→ 当前项目内重写接口/约束/验证
→ Scratch / Candidate
→ Formal
```

## 2. 每张算法卡必须回答的 10 个问题

1. **适用信号**：什么结构出现时才考虑它？
2. **不适用信号**：什么情况下不要用？
3. **输入合同**：数据类型、时间/空间顺序、单位、变量角色是什么？
4. **输出合同**：最终输出是否与题面要求一致？
5. **最小 baseline**：用什么简单方法做公平参照？
6. **升级触发器**：baseline 出现什么失败才升级到该方法？
7. **验证协议**：最能证伪它的测试是什么？
8. **失败模式**：最常见的泄漏、不可行、过拟合或解释错误是什么？
9. **论文证据**：最终最值得保留哪类表/图/结论？
10. **停止/回退**：什么情况下应放弃它？

算法卡不是算法百科，不需要长篇推导评委熟悉的常识。

## 3. 参考代码适配前检查

禁止“复制文件→改列名→直接 Formal”。至少完成：

- 明确题面输入/输出与示例接口是否一致；
- 删除示例数据、示例结论和演示参数；
- 使用项目相对路径，不写本机绝对路径；
- 固定随机种子或记录求解器状态；
- 把数据预处理放在正确的训练/验证边界内；
- 重写单位、约束、损失/目标、评价指标；
- 保存 baseline 与主模型的同口径输出；
- 对关键约束做程序化回查；
- 在项目 runner 中产生可追溯 artifact；
- 只有当前项目真实运行可进入 Formal。

## 4. 模型梯子而非算法菜单

每问默认最多维护：

```text
baseline → main → challenger → fallback
```

新增候选的理由必须是“解决尚未解决的具体失败”，不能是“这个算法更先进/更常见/可能加分”。

### 预测

`seasonal naive → classical/regularized → structured nonlinear → advanced`。

### 分类

`prevalence/logistic → tree ensemble → calibrated advanced model`。

### 排序评价

`equal weight → justified weighting/scoring → stability analysis`。

### 优化

`rule/greedy → LP/MILP/QP/NLP/network → decomposition → heuristic`。

### 机理

`limiting/simple mechanism → calibrated mechanism → additional states/uncertainty`。

能用精确、经典模型清晰解决时，不因“创新感”优先使用元启发式或深度模型。

## 5. 公平 baseline 原则

baseline 不能故意弱化。必须保持：

- 同一输入信息；
- 同一输出定义；
- 同一评价窗口；
- 同一指标和分母；
- 相同约束口径。

如果两个模型输出不同问题，不应放在同一个“模型比较表”中强行排名。

## 6. 题型验证映射

| 方法族 | 首要验证 | 次要验证 |
|---|---|---|
| 时间序列 | rolling/out-of-time + leakage | residual / interval coverage |
| 回归 | holdout + residual | effect interval / robust alternative |
| 分类 | PR/threshold/confusion | calibration / subgroup error |
| 聚类 | stability | interpretability / perturbation |
| 排序 | weight/rank stability | indicator deletion |
| 精确优化 | feasibility + status/gap | small exact case / sensitivity |
| 启发式 | feasibility + exact/relaxation reference | multi-seed + convergence |
| 多目标 | non-dominated set + coverage | knee robustness |
| 机理 | dimension/boundary/conservation | sensitivity / calibration |
| 网络 | graph construction + feasibility | bottleneck / perturbation |

不要机械套“误差+灵敏度+稳健性三件套”。验证必须针对模型最可能失败的环节。

## 7. 图表和论文证据

参考代码生成的示例图只用于理解，不进入正式论文。当前项目重新运行后，优先保留：

- 能回答题面主问题的结果图/表；
- baseline 与主模型的关键差异；
- 最有区分度的失败/稳健性证据；
- 方案、资源、调度、空间或权衡本身。

收敛曲线、特征重要性、相关热力图只有在确实回答 reader question 时才进入正文。

## 8. 常见误用

禁止以下默认行为：

- “随机森林/XGBoost 通常更准，所以先用”；
- “神经网络更高级，所以作为创新”；
- “特征重要性高，所以存在因果影响”；
- “p<0.05，所以实际意义很强”；
- “一个固定权重解就是 Pareto 前沿”；
- “启发式收敛了，所以得到全局最优”；
- “训练拟合很好，所以预测能力强”；
- “每个模型都必须做固定三种检验”；
- “图越复杂越容易加分”。

## 9. README 编写规范

`代码库/<分类>/README.md` 应按统一结构组织：

1. 定位与使用边界；
2. 文件/方法地图；
3. 选择顺序；
4. 适用与不适用条件；
5. baseline 与升级触发器；
6. 数据与实现风险；
7. 验证和失败模式；
8. 建议保留的论文证据；
9. 停止/回退规则；
10. Formal 前重写要求。

README 不维护官方比赛规则，不使用“必考、必做、加分模型、改参数即用”等确定性营销表述。

## 10. 代码模板质量

模板应优先保证：

- 核心函数和示例分离；
- 输入/输出类型明确；
- 随机性可控；
- 失败时显式报错；
- 不偷偷回退到语义不同的算法；
- 指标计算口径明确；
- 图和数据输出可被当前项目重新接管；
- 示例仅演示 API，不声称模型质量。

参考层最终目的不是减少思考，而是**让高质量比较和验证更快开始**。
