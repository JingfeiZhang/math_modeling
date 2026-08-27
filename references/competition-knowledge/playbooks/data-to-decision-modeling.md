---
playbook_id: data-to-decision-modeling
playbook_version: 1
tags: [data-quality, forecasting, pricing, inventory, replenishment, predict-then-optimize, decision]
modules: [statistics-forecasting, statistics-regression-small-sample, optimization-lp-milp, optimization-uncertainty-planning]
stage_scope: [P1, P2, P3a, P3b, P4]
evidence_status: P1-P4-non-evidence
contest_evidence_eligible: false
allowed_use: [data_semantics, temporal_validation, response_modeling, interface_design, error_propagation, decision_evaluation]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 数据 → 预测/关系 → 决策：数据驱动建模手册

> 定位：P1–P4 的“数据分析最终要落到决策”的专项手册，适用于销售、库存、需求、定价、补货、资源配置等题。
>
> 来源基础：CUMCM-2023C 蔬菜类商品自动定价与补货决策讲解中关于异常预处理、时间效应、销量—价格/补货关系、替代与互补、外部数据价值的解题要点，经当前数据质量、预测验证和优化质量标准提炼。历史题的具体模型不是标准答案。

## 1. 这类题的主线不是“做完统计再做优化”

优先识别完整决策链：

```text
原始交易/运营数据
→ 数据质量与生成机制
→ 结构发现
→ 需求/响应关系
→ 预测或情景生成
→ 决策模型
→ 方案验证
→ 数据价值与边界
```

每一层都必须说明它如何服务下一层。

## 2. 交易/运营数据先判断“0、缺失、退货、折扣”分别是什么

历史零售型题的关键经验是：

- 退货不是普通负销量；
- 无销售不一定等于真实需求为 0；
- 折扣/促销会改变价格—销量关系；
- 营业日缺失与系统缺失含义不同；
- 单品下架会导致结构性缺失。

建立字段语义表：

| 字段/现象 | 可能含义 | 处理前必须回答 |
|---|---|---|
| 销量=0 | 无需求/缺货/未营业/未上架 | 哪一种？ |
| 负销量 | 退货/冲销 | 是否合并到原交易？ |
| 低价格 | 折扣/临期/促销 | 是否属于同一价格机制？ |
| 缺日期 | 无交易/数据丢失 | 是否补 0？ |
| 商品消失 | 下架/缺货 | 是否进入预测样本？ |

不能为了方便直接统一填补。

## 3. 时间效应必须先于随机切分

销量、价格、补货常有：

- 周内效应；
- 周末/工作日差异；
- 节假日；
- 季节；
- 趋势；
- 临期/库存周期。

先画/统计这些结构，再选择验证方案。

### 验证原则

```text
训练时间 < 验证时间 < 测试时间
```

scaler、imputer、encoder、特征选择和调参都只能在训练窗口内完成。

## 4. 相关关系必须区分“描述、预测、决策”

例如销量与价格相关，至少存在三种不同问题：

1. **描述**：历史上是否共同变化？
2. **预测**：给定可获得信息，能否提高未来销量预测？
3. **决策**：主动调整价格后，销量将如何响应？

第三个问题比前两个要求更强。相关性或普通 feature importance 不能自动成为价格弹性或因果响应。

若题目要求定价，至少说明：

- 价格是否是可控决策变量；
- 历史价格变化是否有促销/清仓混杂；
- 响应模型在什么价格范围内有效；
- 是否只把关系用于情景而非因果 claim。

## 5. Predict-then-Optimize 的接口必须显式

不要把预测脚本和优化脚本松散串联。

定义上游输出：

```text
forecast_mean[item,t]
forecast_interval/item_scenarios
error_profile
forecast_horizon
```

定义下游输入：

```text
demand_scenario[item,t]
price bounds
inventory state
loss/waste rate
capacity
service target
```

并记录：

- 单位；
- 时间粒度；
- 聚合层级；
- 预测时点；
- 可用信息边界。

## 6. 上游预测误差必须传播到下游

如果优化直接把 `forecast_mean` 当真值，至少补一个下游敏感性或场景测试。

推荐：

```text
point forecast baseline
→ low/base/high scenarios
→ empirical residual scenarios
→ 必要时 robust/stochastic
```

观察：

- 方案是否改变；
- 利润/成本变化；
- 缺货/浪费率；
- 哪些品类最敏感。

只有上游误差会实质改变决策时，才值得升级复杂的不确定性模型。

## 7. 替代性与互补性是“耦合结构”，不是装饰性相关图

如果多个商品/资源之间存在替代或互补，先回答：

- 关系来自题面、数据还是外部知识？
- 是同期关系还是滞后关系？
- 是否受共同季节因素驱动？
- 它如何改变最终选择/约束/目标？

仅仅算相关矩阵而不进入决策模型，不足以证明“考虑了替代互补”。

可迁移方式包括：

- 相似商品聚类后分组决策；
- 交叉价格/需求关系；
- 多样性约束；
- 品类覆盖约束；
- substitution scenario。

## 8. 单品/品类层级不能混用

常见链路：

```text
品类层面：稳定结构、总体需求
↓
单品层面：替代、选择、库存、价格
```

如果 Q1 在品类层面、Q3 在单品层面，需要明确 aggregation / disaggregation 接口。

不要把品类预测误差直接当成单品预测误差。

## 9. 外部数据的价值要用“决策价值”判断

历史题讲解提出可考虑库存、损耗、天气、消费者等外部数据。吸收时采用更严格的准入条件：

新增数据前回答：

1. 它解决哪个已识别失败点？
2. 比赛期间能否合法、稳定获得？
3. 时间/空间粒度能否对齐？
4. 是否会产生未来泄漏？
5. 加入后是否改变预测或最终决策？

如果只提高解释故事、不改变证据或方案，不优先采集。

## 10. Baseline 设计

### 数据/预测 baseline

- last value；
- seasonal naive；
- moving average；
- simple linear/regression。

### 决策 baseline

- 当前运营规则；
- 简单安全库存；
- 固定加价率；
- 每品类独立优化。

主模型必须量化相对 baseline 改善了：

- 预测误差；
- 利润/成本；
- 缺货；
- 损耗；
- 服务水平；
- 稳定性。

## 11. 最有信息量的实验

优先：

1. 时间外 baseline comparison；
2. 高需求/周末/节假日分组误差；
3. point forecast vs uncertainty-aware decision；
4. 有/无替代关系的决策差异；
5. forecast error 对利润/服务水平的传导；
6. failure scenario：缺货、价格波动、损耗上升。

不优先：

- 大量无关模型排行榜；
- 只在训练集比较；
- 为每个参数机械 ±5%、±10%。

## 12. 论文闭环

高质量写法：

```text
数据问题是什么
→ 为什么这样处理
→ 发现了什么结构
→ 结构如何决定预测/关系模型
→ 预测/关系模型如何进入决策
→ 决策相对 baseline 改善多少
→ 对误差/场景是否稳定
→ 哪些数据缺失限制结论
```

不要把“数据分析”“预测”“优化”写成三个互不相干的小论文。

## 13. 2023C 的使用边界

本手册只吸收以下结构：

```text
异常与时间结构
→ 销量/价格/补货关系
→ 未来需求/响应
→ 补货与定价
→ 单品替代/互补
→ 额外数据价值
```

不预设新题一定使用某种回归、时间序列或优化算法。