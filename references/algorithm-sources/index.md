# 算法速查源

这是一个只读的 P1–P3 算法方法源索引。当前仓库以 `JingfeiZhang/1` 的固定提交作为**来源锚点**，并维护 `代码库/` 这一 repo-tracked **curated derivative**：其中可继续修正泄漏、fallback、接口和学术表达问题，因此不保证与上游固定提交字节一致。它仍然不是比赛 Formal Evidence，也不是论文数字、Figure Contract、submission 或 release 的结果来源。

所有算法卡、代码模板和分类 README 统一遵守 [算法参考与模板质量标准](QUALITY_STANDARD.md)，并服从 `references/competition-knowledge/playbooks/academic-quality-standard.md` 的总体学术质量原则。

## 来源与本地修订的区别

- `repository + commit + source_path + source_file_sha256` 描述上游来源和可追溯定位；
- `代码库/` 描述在本仓库继续维护的 study-only 修订版本；
- 本地修订可以修正数据泄漏、静默 fallback、错误统计解释或接口问题，但不改变上游来源记录；
- `reference-library.ps1 -Action sync` 对 `local_directory` 重新索引**当前本地文件**，用于发现本地漂移和检索，不把本地文件冒充上游原始 blob；
- 若需要核对上游原实现，以算法卡的固定 commit URL/sha 为准。

## 权威边界

- 竞赛规则以当年官方文件和当前项目 `contest.yaml` 为最高权威；`代码库/` 中的 README、自检清单和历史经验不具有规则优先级。
- `NO_LICENSE` 源按 `study_only` 处理：可阅读、运行示例、理解算法接口，但不得把其原始实现未经项目内重写与验证直接作为 Formal 代码。
- 外部或本地参考示例的数据、图和数值不能作为比赛证据。
- 选中算法线索后，必须回到当前项目中重写数据接口、单位、约束、随机种子、输出合同和验证流程，并由当前项目运行产生证据。
- `references/algorithm-sources/cards/` 与 `skeletons/` 是主工作台的决策摘要和项目重写骨架，优先于直接浏览 `代码库/`。

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

| source_id | 上游 | 许可状态 | 本地内容策略 | 定位 |
|---|---|---|---|---|
| `github-jingfeizhang-1` | [JingfeiZhang/1](https://github.com/JingfeiZhang/1) @ `8abaef8...` | `NO_LICENSE` | `curated_derivative` | P1–P3 study-only 速查 |

本地目录由 `references/algorithm-sources/sources.yaml` 的 `mirror_relpath` 指定，当前为 `代码库/`；索引目录仍使用固定上游 commit 作为 provenance namespace，但其中的文件哈希对应当前本地 curated 内容。

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

算法卡是决策摘要，不是代码拷贝。卡中的上游 entry-point SHA/URL 用于 provenance；当前本地 curated 文件可能已经发生质量修订。选中候选后仍需回到当前项目 runner 和证据合同中重新实现。

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
