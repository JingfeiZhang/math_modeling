# 算法速查源

这是一个只读的 P1–P3 算法方法源索引。当前仓库包含 `JingfeiZhang/1` 固定提交的本地镜像 `代码库/`，用于离线学习、候选模型发现和 baseline 原型设计；该镜像仍然不是比赛 Formal Evidence，也不是论文数字、Figure Contract、submission 或 release 的结果来源。

所有算法卡、代码模板和分类 README 统一遵守 [算法参考与模板质量标准](QUALITY_STANDARD.md)，并服从 `references/competition-knowledge/playbooks/academic-quality-standard.md` 的总体学术质量原则。

## 权威边界

- 竞赛规则以当年官方文件和当前项目 `contest.yaml` 为最高权威；`代码库/` 中的 README、自检清单和历史经验不具有规则优先级。
- `NO_LICENSE` 源按 `study_only` 处理：可阅读、运行示例、理解算法接口，但不得把其原始实现未经项目内重写与验证直接作为 Formal 代码。
- 外部示例数据、示例图和示例数字不能作为比赛证据。
- 选中算法线索后，必须回到当前项目中重写数据接口、单位、约束、随机种子、输出合同和验证流程，并由当前项目运行产生证据。
- `references/algorithm-sources/cards/` 与 `skeletons/` 是主工作台的决策摘要和项目重写骨架，优先于直接浏览镜像目录。

## 高质量使用路径

```text
题面数学结构
→ academic-quality-standard
→ algorithm card
→ 必要时查看代码库实现思路
→ 当前项目内重写
→ same-output baseline
→ Candidate + falsification probe
→ task-specific validation
→ Formal / claims
```

算法参考不是模型菜单。一个候选方法只有在能说明“触发条件、非触发条件、假设、baseline、失败模式、验证和回退”时才值得进入 Candidate。

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
| `github-jingfeizhang-1` | [JingfeiZhang/1](https://github.com/JingfeiZhang/1) | `NO_LICENSE` | 固定 commit 的 repo-tracked Python 算法镜像，仅用于 P1–P3 study-only 速查 |

镜像目录由 `references/algorithm-sources/sources.yaml` 的 `mirror_relpath` 指定，当前为工作区下的 `代码库`。`reference-library.ps1 -Action sync` 只维护被忽略的 `tools/algorithm-sources/` 索引状态，不改变 Formal Evidence；索引缺失时查询只返回 warning，不联网、不执行外部脚本。

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

算法卡是决策摘要，不是代码拷贝。选中候选后，回到当前项目 runner 和证据合同中重新实现。

每张卡的 `skeleton_path` 指向项目自有重写骨架。骨架只定义输入输出、baseline、约束回查和验证回执；正式运行前必须在当前项目中完成实现并重新记录代码、数据和环境哈希。

## 算法卡的最低学术信息

算法卡至少应覆盖：

- trigger / non-trigger；
- assumptions；
- input / output contract；
- same-output baseline；
- task-matched validation；
- known failure modes；
- upgrade / fallback condition；
- paper evidence and claim boundary；
- project-local reimplementation requirements。

只有 API 和调参说明而没有这些内容的卡片，应视为待升级资料，而不是正式选型依据。

## 覆盖边界

当前 11 张卡覆盖预处理、评价排序、预测、分类聚类、规划优化、元启发式、统计推断、图论网络、机理 ODE、模型验证和组合模型，覆盖国赛常见的预测、评价、优化、机理、数据分析和网络主路径。

仍需按题面临时建模或通过学术文献补充的方向包括复杂 PDE/偏微分数值求解、博弈论、复杂匹配与车辆路径、因果推断、深度学习专项和 MATLAB 专用实现。速查卡只缩短候选发现时间，不能替代题面语义合同、baseline、正式实验和验证。
