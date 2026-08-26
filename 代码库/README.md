# 数学建模国赛 · 编程手算法速查库

> 本目录是 **P1–P3 的离线算法学习与原型参考库**，不是 CUMCM 2026 规则来源，也不是 Formal Evidence、论文数字或最终提交代码的直接来源。
>
> 规则与提交要求以当年官方文件及 `projects/cumcm/2026/contest.yaml` 为准；正式算法使用边界以 `references/algorithm-sources/` 为准。

## 使用原则

1. 可以阅读、运行示例、理解接口、快速比较候选方法。
2. 可以用本目录帮助形成 baseline、主模型候选和风险探针。
3. **不要把示例数据、示例图或示例数值当作比赛证据。**
4. **不要把这里的原始实现直接复制为 Formal 代码。** 选中方法后，应在当前项目 `projects/.../src` / runner 中重写数据接口、单位、约束、随机种子、输出合同和验证流程。
5. Formal、claims、Figure Contract、论文和 submission 只能引用当前项目真实运行并冻结后的证据。
6. 本目录中的经验性 README、自检清单和建议项不覆盖官方规则。

## 推荐使用路径

```text
题意/数据结构
  ↓
references/algorithm-sources/cards/      先看决策卡
  ↓
代码库/                                  必要时查看实现思路和示例
  ↓
当前项目内重写实现
  ↓
Scratch / Candidate
  ↓
baseline + challenger + 专项验证
  ↓
Formal / claims
```

## 快速入口

| 需求 | 目录 |
|---|---|
| 数据导入、清洗、可视化 | `01_数据预处理与可视化/` |
| 评价与排序 | `02_评价类模型/` |
| 预测与时间序列 | `03_预测类模型/` |
| 分类与聚类 | `04_分类与聚类/` |
| 规划与优化 | `05_规划与优化/` |
| GA / PSO / SA / ACO / DE / NSGA-II | `06_智能优化算法/` |
| 统计分析与推断 | `07_统计分析/` |
| 图论与网络 | `08_图论与网络模型/` |
| 微分方程 / 系统动力学 | `09_机理建模/` |
| 误差、灵敏度、稳健性、交叉验证、残差诊断 | `10_模型检验/` |
| 组合模型 | `11_组合模型（创新加分）/` |

完整 CSV/Excel 导入示例见：
`01_数据预处理与可视化/00_CSV数据导入完全指南.py`。

## 模型选择约束

本库不再采用“算法越复杂越好”或“每问都必须套固定模型”的策略。主工作台当前统一遵循：

- 先建立同输出 baseline；
- 主模型优先匹配题意结构、数据条件、可验证性和可解释性；
- 只有已经观察到明确失败点时才增加复杂度；
- 每问默认只维护 baseline / main / challenger / fallback；
- 预测、分类、评价、优化、机理等题型使用与任务匹配的专项验证；
- 结果写作采用“结果 → baseline 比较 → 原因/机制 → 实际意义 → 边界”。

详见：

- `references/competition-knowledge/playbooks/award-oriented-modeling.md`
- `references/competition-knowledge/playbooks/data-and-feature-quality.md`
- `references/competition-knowledge/playbooks/algorithm-routing-quality.md`
- `references/competition-knowledge/playbooks/experiment-design-quality.md`

## 环境隔离

本目录有自己的冻结依赖 `requirements.txt`，用于验证这些历史模板；它 **不是** 主工作台环境定义。

```text
主工作台环境：根目录 environment.yml（workflow / Formal / paper / audit / release）
算法模板环境：代码库/requirements.txt（模板兼容性与离线示例）
```

不要在主工作台环境里直接执行：

```bash
pip install -r 代码库/requirements.txt
```

如需验证本目录模板，应使用隔离环境。`_run_all_tests.py` 中记录的“68/68”是历史验证口径，当前机器是否仍通过必须以实际重新运行结果为准。

## 合规与交付

`00_国赛合规与交付自检清单.md` 仅作为辅助检查入口。官方页数、AI 使用声明、匿名性、附件和提交要求统一读取当前项目 `contest.yaml` 与 root audit，不在本目录重复维护第二套硬规则。

## 素材来源

本目录是在既有建模素材和算法模板基础上整理的离线镜像。其来源、固定 commit、许可状态、使用边界和 Formal 禁止项统一记录在：

`references/algorithm-sources/sources.yaml`
