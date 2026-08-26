# 外部算法速查库

这是一个只读的 P1-P3 算法方法源索引。仓库只保存 GitHub 仓库的 commit、许可状态、代码路径和人工整理的风险卡，不保存外部源码、数据、论文、运行结果或缓存。

## 使用边界

- 只用于题型识别、候选模型、baseline 设计、假设检查和风险探针。
- `NO_LICENSE` 源只能作为学习和阅读入口，不直接复制或再发布代码。
- 外部仓库的示例数据和示例数字不是比赛证据。
- Formal、claims、Figure Contract、论文、submission 和 release 不得引用本层作为结果来源。
- 使用外部实现线索后，必须在当前项目中重写数据接口、单位、约束、随机种子和验证流程。

## 快速查询

```powershell
scripts/reference-library.ps1 -Action lookup -Tags forecasting,time-series -Layer code
scripts/reference-library.ps1 -Action lookup -Tags optimization,multiobjective -Layer code
scripts/reference-library.ps1 -Action lookup -Tags validation,robustness -Layer code
scripts/reference-library.ps1 -Action status
```

## 当前来源

| source_id | 仓库 | 许可状态 | 定位 |
|---|---|---|---|
| `github-jingfeizhang-1` | [JingfeiZhang/1](https://github.com/JingfeiZhang/1) | `NO_LICENSE` | 本地固定 commit 的 Python 算法示例，适合 P1-P3 速查 |

本机代码目录由 `references/algorithm-sources/sources.yaml` 的 `mirror_relpath` 指定，当前为工作区下的 `代码库`。执行 `reference-library.ps1 -Action sync` 后，索引和镜像状态写入被忽略的 `tools/algorithm-sources/`；索引缺失时查询只返回 warning，不联网、不执行外部脚本。

## 算法卡

| 标签 | 算法卡 |
|---|---|
| 预处理、图表 | [preprocess-visualization](cards/preprocess-visualization.md) |
| 评价、排序 | [evaluation-ranking](cards/evaluation-ranking.md) |
| 预测、时间序列 | [forecasting-time-series](cards/forecasting-time-series.md) |
| 分类、聚类 | [classification-clustering](cards/classification-clustering.md) |
| 统计检验、试验设计 | [statistics-inference](cards/statistics-inference.md) |
| 图论、网络 | [graph-network](cards/graph-network.md) |
| 机理、ODE | [mechanistic-ode](cards/mechanistic-ode.md) |
| 组合模型 | [hybrid-models](cards/hybrid-models.md) |
| 规划、整数、多目标 | [optimization-programming](cards/optimization-programming.md) |
| 启发式、NSGA-II | [metaheuristic-search](cards/metaheuristic-search.md) |
| 验证、稳健性 | [validation-diagnostics](cards/validation-diagnostics.md) |

算法卡是决策摘要，不是代码拷贝。选中候选后，回到当前项目的 runner 和证据合同中重新实现。

每张卡的 `skeleton_path` 指向一个项目自有重写骨架。骨架只定义输入输出、baseline、约束回查和验证回执，不包含外部仓库代码；正式运行前必须将其实现复制到当前项目并重新记录代码、数据和环境哈希。

## 覆盖边界

当前 11 张卡覆盖预处理、评价排序、预测、分类聚类、规划优化、元启发式、统计推断、图论网络、机理 ODE、模型验证和组合模型，覆盖国赛常见的预测、评价、优化、机理、数据分析和网络主路径。

仍需按题面临时建模或通过学术文献补充的方向包括复杂 PDE/偏微分数值求解、博弈论、复杂匹配与车辆路径、因果推断、深度学习专项和 MATLAB 专用实现。速查卡只缩短候选发现时间，不能替代题面语义合同、baseline、正式实验和验证。
