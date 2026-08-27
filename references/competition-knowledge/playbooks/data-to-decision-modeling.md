---
playbook_id: data-to-decision-modeling
playbook_version: 1
tags: [data-quality, forecasting, pricing, inventory, replenishment, predict-then-optimize, decision]
modules: [statistics-forecasting, statistics-regression-small-sample, optimization-lp-milp, optimization-uncertainty-planning]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 数据 → 预测/关系 → 决策：数据驱动建模手册

> 来源基础：CUMCM-2023C 蔬菜类商品自动定价与补货决策讲解中关于异常预处理、时间效应、销量—价格/补货关系、替代与互补、外部数据价值的可迁移要点，经当前数据质量、预测验证和优化质量标准筛选。历史题具体模型不是标准答案。

## 触发与排除

**触发**：销售、需求、库存、价格、补货、运营、客流、负荷等数据题，且前一部分的数据分析/预测会影响后一部分的资源配置、定价或策略决策。

**排除**：题目最终只要求描述统计/预测，不存在后续决策；或上游预测变化不会改变任何方案。此时优先使用单独的统计/预测模块，不强行构造“预测→优化”。

核心链：

```text
原始运营数据
→ 数据语义与生成机制
→ 结构发现
→ 预测/响应关系
→ 情景/参数接口
→ 决策模型
→ 端到端评价
```

## 输入输出合同

### 数据语义

先区分：

- `0`：无需求、缺货、未营业、未上架还是数据缺失？
- 负销量：退货/冲销还是错误？
- 低价格：折扣、促销、临期还是正常价格？
- 缺日期：无交易还是数据丢失？
- 商品消失：下架还是缺货？

不能为了方便把这些情况统一填补。

### 预测/关系输出

至少明确：

```text
item/group
forecast_time
train_cutoff
point_forecast
interval/scenario definition
error profile
unit
aggregation level
```

### 决策输入/输出

下游必须明确读取哪个预测/情景字段，以及：

- price bounds；
- inventory state；
- loss/waste rate；
- capacity；
- service target；
- 决策时点能看到的信息。

最终输出应是可执行方案和决策指标，而不是只报告预测误差。

## 分阶段行动

### P1

1. 画出数据流与决策流。
2. 建字段语义表，先处理 `0/缺失/退货/折扣`。
3. 识别时间结构：周内、周末/工作日、节假日、季节、趋势。
4. 区分描述、预测和决策三个问题。
5. 识别品类/单品等层级接口。

### P2

建立两端 baseline：

- 预测：last value / seasonal naive / moving average / simple regression；
- 决策：当前规则 / 固定加价率 / 简单安全库存 / 每品类独立优化。

验证严格遵循时间边界：scaler、imputer、encoder、特征选择和调参只能在训练窗口拟合。

### P3a

建立一个低复杂度预测/响应主模型，再接一个最窄决策模型。

检查：

- 销量—价格/补货关系是否只是相关；
- 预测误差集中在哪些高代价时段；
- 单品/品类接口是否守恒；
- 改进预测是否真的改善决策指标。

### P3b

只针对观察到的失败升级：

- 峰值/周末误差大 → 修预测或分组结构；
- point forecast 导致方案不稳 → 加 low/base/high 或 residual scenario；
- 替代/互补会改变决策 → 加耦合结构；
- 外部数据能显著改善决策 → 再采集/接入。

如果预测 MAE 改善但最终利润、成本、服务水平或方案不变，不继续升级预测模型。

## baseline 与升级

推荐端到端梯子：

```text
朴素预测 + 当前/规则决策
→ 低复杂度预测 + 确定性决策
→ 分组/响应结构 + 同一决策模型
→ 预测误差情景 + 场景复算
→ 有证据时才做 robust/stochastic
```

升级必须回答：

1. 当前链路的主要失败点在哪里？
2. 新模型改变的是预测、响应关系还是决策层？
3. 最终决策指标改善多少？
4. 是否只在训练集/单一时段成立？

## 联合诊断

### 1. 时间与泄漏

```text
训练时间 < 验证时间 < 测试时间
```

任何未来价格、未来需求、未来促销等不可作为决策时点已知特征。

### 2. 描述、预测、决策边界

历史上销量与价格相关，不自动意味着主动调价会产生同样响应。若题目要求定价，至少说明：

- 价格是否是可控变量；
- 历史价格是否受促销/清仓混杂；
- 响应关系在哪个价格范围内有效；
- 当前结果是相关/预测关系还是因果 claim。

### 3. 误差传播

把上游误差传入下游，观察：

- 方案是否改变；
- 利润/成本；
- 缺货/浪费；
- 服务水平；
- 哪些 item/group 最敏感。

### 4. 替代与互补

相关矩阵本身不等于“考虑了替代/互补”。只有关系进入：

- 情景；
- 需求响应；
- 多样性/覆盖约束；
- 分组选择；
- 交叉影响；

并改变最终方案时，才有决策价值。

### 5. 层级一致性

如果 Q1 在品类层面、后续在单品层面，必须明确 aggregation/disaggregation；不能把品类预测误差直接当单品误差。

### 6. 外部数据价值

新增库存、损耗、天气、消费者等数据前回答：

- 解决哪个失败点？
- 是否合法稳定获得？
- 粒度能否对齐？
- 是否产生未来泄漏？
- 是否改变最终决策？

若只丰富故事、不改变模型或证据，不优先采集。

## 停止与回退

停止条件：

- 数据语义已澄清；
- 时间验证无泄漏；
- 预测/关系 baseline 可比；
- 最终决策相对规则 baseline 有稳定收益，或简单方案已足够；
- 预测误差传播后主要结论仍成立，或失败边界明确；
- 更复杂模型不再改变决策。

回退：

- 复杂预测不稳定 → seasonal/simple baseline；
- 相关结构不能支持响应解释 → 降级为预测/情景关系；
- 替代/互补不改变决策 → 删除耦合；
- robust/stochastic 不改变方案 → 确定性模型 + 场景报告。

## Candidate 交接

Candidate 至少交接：

- 字段语义/异常处理说明；
- 时间切分与 train cutoff；
- 预测/响应 baseline 与主模型；
- 上游输出到下游输入的字段、单位和粒度；
- 端到端 baseline；
- 最终决策指标；
- 预测误差/场景传播结果；
- 替代/互补或外部数据是否保留的证据；
- 当前 claim 边界。

CUMCM-2023C 只用于说明“异常/时间结构 → 关系/预测 → 补货/定价 → 替代/互补 → 外部数据价值”的迁移链，不携带具体模型名称或历史参数。

## 禁止事项

- 不把无销售直接等同真实需求为 0；
- 不随机切分有时间依赖的数据；
- 不用未来信息拟合预处理器或特征；
- 不把相关/feature importance 写成价格因果弹性；
- 不只优化预测指标而忽略最终决策指标；
- 不把相关矩阵本身当作替代/互补模型；
- 不机械采集所有可获得外部数据；
- 不引用本手册或历史培训资料作为 Formal/论文证据。