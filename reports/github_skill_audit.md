# GitHub 数学建模 Skills 审计报告

审计日期：2026-08-01；增量复核：2026-08-03。目标是为 2026 CUMCM 优先配置可用于建模求解、论文写作、绘图与终稿审查的 Codex skills。

## 结论

安装采用“一个主流程 + 两个专业模块”的最小互补组合：

1. [`handsomeZR-netizen/mathmodel-skill`](https://github.com/handsomeZR-netizen/mathmodel-skill) 的 `mathmodel-skill` 作为主工作流；
2. [`Lupynow/math-modeling-skills`](https://github.com/Lupynow/math-modeling-skills) 的 `math-modeling-solver` 作为算法与代码模板库；
3. 同仓库的 `math-modeling-paper` 作为数模论文写作与自审模块。

三者均使用 MIT 许可证并锁定到精确提交。论文级绘图继续使用本机已有的 `ccf-visual-composer` 与 `nature-figure`，LaTeX/PDF 使用 `latex-document-skill` 与 `pdf`。

2026-08-03 又复核了 `Lupynow/math-modeling-skills`、`jihe520/MathModelAgent` 与 `zhnnky329/MathModeling-skills`。本次不增加全局 Skill 名称，只将独特模式写入 `modeling-paper-studio/references/upstream-skill-patterns.md`，保持“单一 orchestrator + 专业子模块”的结构。

## 候选比较

| 仓库 | 搜索快照 | 许可证 | 结构与资源 | 结论 |
|---|---:|---|---|---|
| `handsomeZR-netizen/mathmodel-skill` | 168 stars，2026-07-22 推送 | MIT | Codex 元数据、10 阶段状态机、三赛事配置、LaTeX 模板、9 个脚本、66 项测试 | 安装主流程 |
| `Lupynow/math-modeling-skills` | 162 stars，2026-07-31 推送 | MIT | 2 个独立 skills、64 个 references/代码模板，覆盖优化、预测、评价、机理、ML 与论文写作 | 安装两个模块 |
| `zhnnky329/MathModeling-skills` | 371 stars，2026-07-23 推送 | MIT | 28 个 Codex 模块，职责拆分细、证据门禁严格 | 不安装；与现有全局 skill 名称冲突 |
| `jihe520/MathModelAgent` | 3.1k stars，2026-08-03 页面快照 | 个人免费/非商业条款 | 6 阶段主流程、Typst/LaTeX 模板、验收脚本、11 类科研组合图模板 | 不整套安装；吸收交接和图型规则 |
| `XiaoMaColtAI/math-modeling-skill` | 549 stars，2026-07-29 推送 | 未检测到 | 算法库、角色文档、模板和工具丰富 | 不安装；缺少明确许可证 |
| `capwitf/My-MathModeling-skills` | 18 stars，2026-07-19 推送 | MIT | `math-figure` 有证据行、DPI/格式检查和结果表 profiling 脚本 | 静态审计通过；GitHub 传输失败且已有成熟替代 |

stars 与推送时间是审计当日的 GitHub 快照，只用于维护性参考，不代表论文质量或获奖保证。

## 2026-08-03 增量整合

三项上游提交均已核验：Lupynow 为 `3a9428c006cc1b977c6a72a531b739a62868a4bc`，zhnnky 为 `50a2942007a98e74cd0948b44d7cb8e4826d15c9`，MathModelAgent 为 `11f38624cd9128bc2ce22d7b3254106e624490cd`。前两项与本地固定提交一致。

吸收的模式：

- 从 zhnnky 吸收按子问题检查的门槛、可运行基线、备用模型触发条件、风险探针、人工判断记录、冻结数字和按语义影响回检。
- 从 MathModelAgent 吸收“分析报告 -> 代码与实验 -> 数据图/非数据图 -> 写作 -> 验收”的明确接口，以及 SHAP 组合图、配对云雨图、交叉验证 ROC 区间、Taylor 图、预测边缘分布、相关矩阵组合图、环形热图与和弦图等图型的选择规则。
- 保留 Lupynow 已安装的求解与写作库，不复制其现有参考和代码模板。

明确拒绝的做法：

- 不安装 MathModelAgent 的 `1start-mathmodel` 或 zhnnky 的 `workflow-orchestrator`，以免与 `mathmodel-skill` 争夺状态所有权。
- 不安装 zhnnky 的 `code-reviewer` 等通用名称，避免覆盖全局同名 Skill。
- 不直接运行 MathModelAgent 的整套应用、`Bash(*)` 流程或 Linux/Claude 绝对路径脚本。
- 不把科研绘图模板的模拟数据输出放入正式论文；模板只能提供布局，正式图必须绑定本题实验文件。
- 不提前创建 `decision_log.json`、正式 Figure Contract 或比赛实验链；这些仍在题面公布并由用户启动主流程后初始化。

## 安全与可用性检查

- 安装前读取了目标 `SKILL.md`、许可证、脚本与依赖文件；没有执行第三方仓库提供的安装脚本。
- `mathmodel-skill` 的网络访问只出现在显式的优秀论文维护/下载脚本中；主流程和 doctor 可离线运行。
- 子进程用途主要是 Pandoc、XeLaTeX 和本地脚本调用；未发现上传工作区、读取凭据或静默安装依赖的代码。
- `mathmodel-skill` 的 CUMCM doctor 实测为 12 项通过，唯一警告是比赛状态尚未初始化；XeLaTeX、ctex 与 Pandoc 均通过。
- 主仓库 66 项单元测试中多数通过；历史错误集中于缺少可选包和 Windows 中文控制台子进程解码。当前工作台按 local-first 策略使用覆盖率最高的现有 Conda 环境；仅在需要扩展能力时创建 `math-modeling`。
- `math-modeling-solver` 的全部 Python 模板通过 `compileall` 语法检查。
- zhnnky 的 `.codex/skills` 主要是声明式 Markdown；仓库 `.claude/settings.json` 含 `rm -rf` 权限模式，因此没有复制或启用该配置。
- MathModelAgent 是完整 Web 应用与 Skill 集合，含后端、前端、Docker、联网检索和 `Bash(*)` 权限声明；本次没有执行其安装、应用代码或第三方脚本。

静态审计不能证明第三方代码绝对安全。锁文件采用精确提交；更新前必须重新比较源码和测试结果。

## 路由建议

- 新比赛、恢复进度、规则与提交门禁：`mathmodel-skill`。
- 拆题、模型选择、优化/预测/评价/仿真与代码模板：`math-modeling-solver`。
- 摘要、正文、模型验证、结果分析、引用与论文自审：`math-modeling-paper`。
- 论文图表：`ccf-visual-composer`；需要科学示意图时再用 `nature-figure`。
- LaTeX 编译、渲染检查与 PDF 预检：`latex-document-skill` + `pdf`。
- 跨 Skill 交接、基线/冻结门槛和组合图适用性：`modeling-paper-studio` 的 `upstream-skill-patterns.md` 与 `scientific-figures.md`。

不要同时启动多个端到端数模 orchestrator；由 `mathmodel-skill` 维护主状态，其他模块只处理当前明确子任务。
