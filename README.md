# 数学建模竞赛写作与绘图工作台

This workspace is organized around reproducible experiments, frozen evidence, a single-source XeLaTeX manuscript, and an auditable submission pipeline. The primary active example is the isolated `cumcm-2026` project; the corpus also indexes MCM/ICM, MathorCup, APMCM, and Huashu Cup examples.

## Quick start

```powershell
# 列出并初始化隔离项目；这不会创建正式题目或赛事状态
powershell -ExecutionPolicy Bypass -File .\scripts\project.ps1 -Action list
powershell -ExecutionPolicy Bypass -File .\scripts\project.ps1 -Action scaffold -Project cumcm-2026

# 赛前：显式选择项目，只检查环境、模板和语料
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action preflight
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action status
powershell -ExecutionPolicy Bypass -File .\scripts\verify_env.ps1 -Tier core

# 仅在题目需要高级优化器或 OCR 时创建本地扩展环境
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -Tier extended
powershell -ExecutionPolicy Bypass -File .\scripts\verify_env.ps1 -Tier full

# Verify MATLAB and generate the publication-figure demo.
powershell -ExecutionPolicy Bypass -File .\scripts\run_matlab.ps1 `
  -Script .\matlab\smoke_test.m
powershell -ExecutionPolicy Bypass -File .\scripts\run_matlab.ps1 `
  -Batch "addpath(genpath('D:/数学建模/matlab')); demo_publication_figure('D:/数学建模')"
```

Shared environments, Skills, corpus, templates, workflow code, and the figure palette remain at the workbench root. Each registered project under `projects/<competition>/<year>/` owns its own `contest.yaml`, problem data, code, experiments, claims, paper, state, and output. New contest commands must always pass `-Project`; the root `contest.yaml` remains only for backward-compatible demos.

## Workspace layout

The root-level `paper/`, `problems/`, `experiments/`, `results/`, and `figures/`
directories are retained as `legacy-demo` compatibility areas. New competition
work must use `projects/<competition>/<year>/`. Shared resources remain in
`config/`, `templates/`, `corpus/`, `src/`, `scripts/`, and `matlab/`.

Workbench-level generated files are grouped as follows:

- `output/_verification/`: test, template, environment, and PDF verification;
- `output/_demos/`: MATLAB and Origin evaluation outputs;
- `output/_archive/`: preserved temporary and historical artifacts;
- `output/`: operational reports required by the workflow; isolated projects place verification snapshots in `output/_verification/` and sealed upload artifacts in `output/release/`.

Inspect or normalize the layout without deleting files:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\workspace.ps1 -Action inspect
powershell -ExecutionPolicy Bypass -File .\\scripts\\workspace.ps1 -Action preview
powershell -ExecutionPolicy Bypass -File .\\scripts\\workspace.ps1 -Action normalize
powershell -ExecutionPolicy Bypass -File .\\scripts\\workspace.ps1 -Action verify
```

## Competition-day workflow

V7 使用 `config/prompt_policy.yaml` 按当前 P 阶段和角色装配短提示，同时保留 V6 的实验、证据和 G0--G6 运行链。Scratch/Candidate 推进优先，Formal/G5/G6 严格收束；不要让一次 `scratch` 试跑或外部论文结果直接进入正文 claims。

查看某个角色实际收到的提示，不会创建比赛状态或修改正式证据：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action prompt -Stage P3a -Role solver -Question Q1
```

命令只写入 `output/_verification/prompts/`。默认回执固定为 `status/objective/conclusion/evidence/warnings/next_action/decision_request`；只有主模型、fallback、claim 范围、官方规则冲突和发布阻断请求人工决策。

### 最短可执行路径

逻辑顺序如下：

```text
initialize
  -> literature-plan -> literature-search/register -> literature-read -> literature-synthesize（与 baseline、Scratch 并行）
  -> run scratch + quickcheck
  -> run candidate + checkpoint
  -> promote
  -> formal G3/G4 + freeze
  -> paper-evidence（仅在论文确有诊断量缺口时）
  -> figure-data -> figure-intent
  -> figure-brief -> figure-render -> figure-qa -> figure-promote（仅当决定绘图时）
  -> layout-check + build
  -> literature-audit + audit -> package -> seal -> verify-release
  -> archive-work
```

`quickcheck` 当前检查已经生成的 `scratch/candidate` run manifest，因此第一次非正式 `run` 之前单独执行不会通过。可比较 baseline 也不是独立命令：它必须写入实验配置的 `methods`，并与主模型产生同类输出；默认 `checkpoint` 只检查输入输出和单位合同、输出守恒、指标定义、核心硬约束、同输出 baseline 与晋升价值。固定种子、确定性复跑、完整哈希、图件 Brief、文献和排版会以 warning/deferred 记录，不拖慢候选探索；输出中的 `PASS_WITH_WARNINGS` 表示当前动作通过但仍有正式化待办，`BLOCK_TRANSITION` 只阻断当前转换。新配置默认是 `run_mode: scratch`，需要形成候选时显式使用 `run_mode: candidate`；schema v2 的 `run_mode: formal` 禁止直接运行，正式目录只能由 `promote` 创建。实验 schema v1 仅用于旧项目兼容，新实验必须使用 v2；新建问题清单使用 question schema v3，v1/v2 继续兼容读取。

```powershell
# 1. 用真实题面初始化，只生成实际存在的 Q1--Qn
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action initialize -Problem C `
  -ProblemFile .\projects\cumcm\2026\problems\incoming\official-C.pdf

# 2. 先跑最小 scratch；配置中必须写清 runner、输入、输出、指标和 baseline
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action run -Question Q1 `
  -Config .\projects\cumcm\2026\experiments\configs\C-Q1-scratch.yaml
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action quickcheck -Question Q1

# 3. 主模型和同输出 baseline 完整后运行 candidate，并做晋升检查
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action run -Question Q1 `
  -Config .\projects\cumcm\2026\experiments\configs\C-Q1-candidate.yaml
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action checkpoint -Question Q1

# 4. 只晋升通过 checkpoint 的 run；formal 不能直接 run
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action promote -Question Q1 -RunId <candidate-run-id>

# 5. 正式 run 通过 G3，冻结已核验 claims，再复核 G4
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action validate -Gate G3 -Question Q1 -StrictManifest
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action freeze -Question Q1 -DecisionId D-Q1-01
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action validate -Gate G4 -Question Q1 -StrictManifest

# 6. 仅当论文缺少诊断、敏感性、机理或绘图支撑量时，从 formal 派生 paper evidence
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action paper-evidence -Question Q1 `
  -Config .\projects\cumcm\2026\experiments\configs\C-Q1-paper-evidence.yaml `
  -StrictManifest

# 7. 每个前置部分/问题完成后做隔离预览；full 通过后构建正式 PDF
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action layout-check -PreviewCheckpoint Q1
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action layout-check -PreviewCheckpoint full
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action build -StrictManifest

# 8. 深审、白名单打包、封存和独立复核必须按顺序执行
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action audit -StrictManifest
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action package -StrictManifest
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action seal -StrictManifest
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 -Project cumcm-2026 -Action verify-release

# 9. 发布复核完成后，移走仍位于 scratch 层的非正式工作目录
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action archive-work
```

以上配置路径是命名约定，不是工作台预置文件；每个项目应从 `templates/workflow/experiment.yaml` 建立自己的配置。若只需要一个候选 run，可以省略单独的 scratch，但仍须先执行该 run 的 `quickcheck` 和 `checkpoint`，再 `promote`。

`-StrictManifest` 不是 Scratch/Candidate 的默认参数。它用于主动兼容性审计，以及 Formal 的 G3/G4 和发布阶段的 G5/G6。Candidate 即使返回 `PASS_WITH_WARNINGS` 也可以继续试错；`promote` 会拒绝尚未证明确定性的候选，但不再要求候选阶段预先完成两次复跑。进入 Formal 后，G3 仍会核验至少一次独立复跑，通常对应 manifest 的 `replay.count >= 2`。

### P0--P6 与 G0--G6

P 层表示时间预算，G 层表示证据成熟度，两者不是一一对应的状态机。P 层回答“比赛已经走到什么时间，应把精力放在哪里”；G 层回答“当前产物是否具备进入下一环节的证据”。`mathmodel-skill` 仍是唯一赛事状态所有者，G 报告只是派生检查。

| 时间阶段 | 比赛进度 | 主要责任 |
|---|---:|---|
| P0 | 赛前 | 环境、规则、模板和空项目骨架；不得创建正式题目状态 |
| P1 | 0%--5% | 题面分解、问数、输入输出、依赖关系、检索计划和论文骨架 |
| P2 | 5%--20% | 每问至少一个可执行、同输出的 baseline；并行完成文献初筛 |
| P3a | 20%--45% | 最小主模型、第一套完整结果和围绕候选模型的定向精读 |
| P3b | 45%--60% | 稳健性、候选比较和模型收束；60% 时锁定主模型 |
| P4 | 60%--75% | formal run、冻结 claims 和正文主干 |
| P5 | 75%--85% | 图表、表格、增量排版和受控 paper evidence |
| P6 | 85%--100% | 85%--95% 完成 G5/G6、白名单附件和封存；最后 5% 只修阻断项，不引入新模型或新主结果 |

| 门禁 | 证明对象 | 是否执行深度 PDF/附件审计 |
|---|---|---|
| G0 | 题面、问题接口和评价口径已形成 | 否 |
| G1 | 主模型、同输出 baseline 和回退边界已筛选 | 否 |
| G2 | 假设、风险探针和关键人工决策已记录 | 否 |
| G3 | formal 实验、指标、约束和复跑证据可审核 | 否 |
| G4 | claims 已冻结，数值、单位、定位和哈希一致 | 否 |
| G5 | 正文结构、证据覆盖、学术文献、引用和 Figure Contract 完整 | 仅静态 LaTeX/合同检查 |
| G6 | PDF 视觉、字体、匿名性、附件白名单和发布完整性通过 | 是 |

因此 G0--G4 不因图件未定稿、文献卡片尚未齐备、参考文献未补齐或排版尚粗糙而阻塞算法推进；这些内容在早期只产生 `LITERATURE_INCOMPLETE` 等 warning。深度文献引用审计、PDF、字体、重叠、留白、包内容和 release 哈希检查集中在 G5/G6，但 `layout-check` 应在前置章节和每问写完后增量运行，避免把版面问题全部拖到发布阶段。

### 学术文献驱动的模型探索链路（V6）

文献链只使用期刊、会议、预印本和学位论文，用于提出候选模型、参数范围、同输出 baseline、风险探针和验证方案。它不使用历届竞赛论文指导模型选型，也不把外部论文的性能数字、模拟数据或图件当作本项目证据。模型能否晋升仍由题面适配、Formal 实验和本项目复跑结果决定。

```text
问题接口
  -> search_plan.yaml
  -> searches/<search-id>/search_receipt.json
  -> cards/<paper-id>.yaml
  -> model_evidence_brief.yaml
  -> question.yaml literature 引用交接
  -> G5 literature-audit
```

每问初次检索默认不超过 20 分钟，项目总计不超过 90 分钟；达到预算后继续 baseline 和 Scratch，不等待文献完备。标题/摘要初筛最多保留 10 篇，每问通常定向精读 2--4 篇，只有中心模型证据不足时才扩展到 6 篇。以 DOI 为主键去重；无 DOI 时按标准化标题、第一作者和年份去重。

四个模板位于 `templates/workflow/literature_search_plan.yaml`、`templates/workflow/literature_search_receipt.yaml`、`templates/workflow/literature_reference_card.yaml` 和 `templates/workflow/literature_model_evidence_brief.yaml`。所有路径必须位于所选项目内，PDF 和网页缓存放在项目临时缓存并由 Git、附件和发布目录排除。

```powershell
# 1. 从 Q1 的问题接口生成场景检索式和方法/约束检索式
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-plan -Question Q1

# 2. 运行一个有时间预算的检索；也可用 literature-register 登记用户提供的 DOI、PDF 或数据库记录
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-search -Question Q1 `
  -Config .\projects\<competition>\<year>\problems\C\questions\Q1\literature\search-config.yaml
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-register -Question Q1 `
  -Config .\projects\<competition>\<year>\problems\C\questions\Q1\literature\register.yaml

# 3. 对保留论文定向精读，卡片必须给出章节、公式、表格或页码定位
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-read -Question Q1 `
  -Config .\projects\<competition>\<year>\problems\C\questions\Q1\literature\read.yaml

# 4. 综合候选模型、baseline、参数依据、风险探针和未解决冲突
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-synthesize -Question Q1 `
  -Config .\projects\<competition>\<year>\problems\C\questions\Q1\literature\synthesis.yaml

# 5. G5 前核对元数据、阅读深度、BibTeX、正文引用、哈希和模型交接
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action literature-audit -Question Q1 -StrictManifest
```

`initialize` 会为每个真实子问题自动生成第一版 `search_plan.yaml`。若之后修改了该问的任务类型、输入输出、关键约束或问题接口，应重新执行 `literature-plan`；该动作会刷新问题接口哈希并清空该问旧的检索、卡片和综合交接引用，防止新问题定义继续消费旧文献结论。模型选择、实验和论文状态属于下游产物，不会单独使原始检索计划失效；若模型选择与 Brief 不一致，G5 会要求重新综合或明确解释差异。

阅读深度为 `METADATA_ONLY`、`ABSTRACT_SCREENED`、`TARGETED_READ` 或 `DEEP_READ`。前两级只能发现候选，不能支撑精确公式、参数范围或方法性能论述；G5 的实质性引用至少需要 `TARGETED_READ`。如果论文提出与当前模型相冲突的严重反例，记录 `MODEL_REVIEW_SUGGESTED`，但不自动阻塞 Formal；G5 前必须解释或解决仍然影响主模型适用性的冲突。

文献内容不单列“文献综述”章节，而是按论证责任进入问题分析、模型选择、参数依据和模型检验。`paper/references.bib` 只保留正文实际引用且元数据已核验的条目。论文 PDF、网页缓存、筛选日志和内部文献卡片均不进入 G6 附件白名单。

### Formal 与 Paper Evidence

- `scratch` 和 `candidate` 都是非正式证据，不得生成 claims、正式 Figure Contracts 或正文性能结论。
- `promote` 将通过 checkpoint 的 run 复制到 `experiments/<problem>/<question>/formal/<run-id>/`，并把 formal manifest 接入该问的 `question.yaml`。正式结果使用固定输入、种子、环境和哈希。
- formal 进入 G4 后视为不可变。源代码、输入、产物哈希、主指标值或单位发生漂移时，原冻结 claim 失效；只重跑受影响问题的 G3/G4，并重新冻结受影响 claim，不覆盖其他问题的正式证据。
- `paper-evidence` 配置必须使用 `run_mode: paper-evidence`，同时引用 schema v2 formal 的 `source_run_id`、父 manifest 路径与 SHA-256。它只允许诊断、敏感性、机理解释和绘图支撑派生，不允许修改主模型，也不会把新性能数字自动写进论文。
- 若 formal 当前主指标不再等于其快照，或 paper-evidence 的主指标值/单位与 formal 不一致，manifest 返回 `REOPEN_REQUIRED`。该分支不得进入图表或正文，必须回到受影响问题的 formal G3/G4；不能用 paper-evidence 绕过冻结。
- 状态为 `READY` 只表示派生量与 formal 主指标一致，后续仍需绑定证据定位、哈希、表格或 Figure Contract。正式图继续要求 PDF、可编辑文字 SVG 和 400 dpi PNG。

### 可视化设计前置链路（V5）

模型输出数据后，先回答“读者需要从这份证据中看到什么”，再决定是否绘图及如何编码。`visualization-design` 只负责图型选择、视觉编码、叙事和设计审查；它不拥有赛事状态、不冻结 claim，也不替代 `modeling-paper-studio` 的 Figure Contract 与 G5/G6 审计。

```text
模型运行输出
  -> figure_data_manifest.yaml
  -> visual_intent.yaml
  -> figure_briefs/fig-*.yaml
  -> figure-staging/fig-*/outputs + figure_qa.json
  -> paper/figure_contracts.yaml design_handoff
  -> paper/figures/ PDF + editable-text SVG + 400 dpi PNG
```

三个配置模板位于 `templates/workflow/figure_data_manifest.yaml`、`templates/workflow/visual_intent.yaml` 和 `templates/workflow/figure_brief.yaml`。复制到所选项目后，必须替换问题、run、相对路径、字段、单位、统计定义和占位哈希；`figure-data` 会从当前 run manifest 和实际源文件重新计算正式来源信息。模板和合成 fixture 的 `contest_evidence_eligible` 必须保持 `false`，只有 Formal 或通过 G4-paper-evidence 的结果才可能由工作流派生为 `true`。

六个动作必须显式指定项目，且渲染只能写入该 run 的 `figure-staging/`：

```powershell
# 1. 校验源文件、字段、单位和哈希，生成 run-local figure_data_manifest.yaml
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-data -Question Q1 -RunId <run-id> `
  -Config .\projects\<competition>\<year>\experiments\configs\Q1-figure-data.yaml

# 2. 决定 figure / table / text / none，并记录最多三个候选图型
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-intent -Question Q1 -RunId <run-id> `
  -Config .\projects\<competition>\<year>\experiments\configs\Q1-visual-intent.yaml

# 3. 只有 artifact_decision=figure 才建立完整 Figure Brief
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-brief -Question Q1 -RunId <run-id> `
  -Intent .\projects\<competition>\<year>\experiments\C\Q1\<level>\<run-id>\visual_intent.yaml `
  -Config .\projects\<competition>\<year>\experiments\configs\Q1-figure-brief.yaml

# 4. 按 Brief 的非 shell render_command 绘制到 run-local staging
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-render -Question Q1 -RunId <run-id> `
  -Brief .\projects\<competition>\<year>\experiments\C\Q1\<level>\<run-id>\figure_briefs\fig-q1-main.yaml

# 5. 检查来源、尺寸、字号、单位、遮挡、裁切、灰度和三件套
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-qa -Question Q1 -RunId <run-id> `
  -Brief .\projects\<competition>\<year>\experiments\C\Q1\<level>\<run-id>\figure_briefs\fig-q1-main.yaml `
  -Outputs .\projects\<competition>\<year>\experiments\C\Q1\<level>\<run-id>\figure-staging\fig-q1-main\outputs

# 6. 根 Agent 负责把已批准、QA 通过且绑定冻结 claim 的图晋升到正式合同与 paper/figures
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project <project-id> -Action figure-promote -Question Q1 -FigureId fig-q1-main `
  -Brief .\projects\<competition>\<year>\experiments\C\Q1\formal\<run-id>\figure_briefs\fig-q1-main.yaml `
  -Qa .\projects\<competition>\<year>\experiments\C\Q1\formal\<run-id>\figure-staging\fig-q1-main\figure_qa.json
```

`workflow.ps1` 提供路由标记，真正的治理边界是 Brief 中已存在且可核验的根 Agent `decision_log` 决策引用；该标记不是操作系统级身份认证，worker 不得据此自行执行晋升。

`figure-qa` 自动核对来源哈希、格式、SVG 可编辑文字、注册颜色、PNG DPI 和物理宽度；标签碰撞与论文页内遮挡仍须在最终尺寸下人工查看，并在 `label_strategy.collision_checked: true` 后才可通过。它不把布尔确认伪装成自动几何检测。

证据形式在 `visual_intent.yaml` 中一次性确定：

| 决策 | 适用情况 | 后续动作 |
|---|---|---|
| `figure` | 趋势、分布、结构、机制或权衡需要视觉编码 | 继续 Brief、render、QA 和 Formal promote |
| `table` | 读者需要核对精确数值，且行列规模可扫描 | 停止绘图链；保留 intent，将表格绑定同一冻结证据 |
| `text` | 单个数值或一句比较比图表更清楚 | 停止绘图链；正文使用冻结 claim，不创建 Figure Contract |
| `none` | 数据不承担论文论证，或与已有证据重复 | 停止绘图链；记录不采用理由，避免装饰性图件 |

生命周期由 run-local 文件和哈希派生，不创建第二套全局状态：

```text
DATA_READY -> INTENT_READY -> BRIEF_READY -> DESIGN_APPROVED
           -> RENDERED -> QA_PASSED -> CONTRACT_READY
```

Scratch 只能推进到 intent，Candidate 最多形成 reviewed Brief 和预览，Formal 或状态为 `READY` 的 Paper Evidence 才能批准设计。任何源数据、run manifest、输入、代码或设计哈希漂移都会使交接变为 `STALE`；若主指标、单位、模型选择或硬约束发生变化，则返回 `REOPEN_REQUIRED`，只重开受影响问题的 G3/G4。`figure-promote` 是唯一把 staging 三件套复制到 `paper/figures/` 并更新正式 `design_handoff` 的动作。

### 目录与白名单

| 目录 | 唯一职责 | 不得放入 |
|---|---|---|
| `experiments/` | `scratch/candidate/formal/paper-evidence` 运行及 manifest | 手填论文数字、未登记正式结论 |
| `results/` | 审核后的结果与冻结 claims | 临时日志、缓存、论文草稿 |
| `paper/` | 唯一 TeX 正文源、正式表图和 Figure Contracts | 第二套 Markdown 正文、历史图件 |
| `src/submission/` | 附件白名单的可运行源码与必要说明 | 整个项目副本、原始赛题和缓存 |
| `output/_verification/` | 预览页、审计 JSON 和过程报告 | 上传文件 |
| `output/_archive/` | scratch 试跑、失败探针和临时构建归档 | formal 证据、冻结 claims |
| `output/release/` | 最终可上传 PDF 和 ZIP | 日志、源码树、历史候选、重复图件 |

`package` 从 `src/submission/` 按显式白名单生成附件，不能先复制整个项目再做删除过滤。`output/release/` 只允许赛事 profile 确定的论文 PDF 和支撑 ZIP；原始题面、内部状态、缓存、历史实验、预览页、审计报告和未登记文件均留在项目其他目录。`seal` 固定最终清单和哈希，`verify-release` 从封存结果独立复核；两者通过后再执行 `archive-work`，将仍位于 scratch 层的非正式运行移到 `output/_archive/`。

Initialization derives the real question count from the supplied problem and creates only the corresponding Q1--Qn manifests and TeX sections. It also writes `paper/generated/question_structure.tex`, so a three-question problem never retains an empty fourth chapter. New V7 prompt projects continue to use `question.yaml` schema v3, which preserves the v2 problem/model/evidence/paper handoff and adds a literature block containing only project-local paths, SHA-256 values, BibTeX keys, and derived status. It never copies literature conclusions or project result values into the question manifest. Legacy schema v1/v2 remains readable for archived projects; use `-StrictManifest` at Formal/G3/G4 or release time when the complete v3 handoff is intended, rather than on every early exploratory run.

`layout-check` 与兼容入口 `preview` 使用同一套隔离预览。可在以下检查点编译：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action preview -PreviewCheckpoint frontmatter
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action preview -PreviewCheckpoint Q1
powershell -ExecutionPolicy Bypass -File .\scripts\workflow.ps1 `
  -Project cumcm-2026 -Action preview -PreviewCheckpoint full
```

Use `frontmatter` after the first four chapters, `Q<number>` after completing each question, and `full` after manuscript assembly. Preview PDFs and rendered pages stay under `output/_verification/previews/`; they are never submission evidence or upload files.

When work contains at least two independent useful streams, lightweight agent delegation is enabled by default. Workers receive a bounded objective, read scope, unique write scope, and expected output; no Sprint manifest or task package is required. The root agent alone changes `state/decision_log.json`, frozen claims, formal `paper/main.tex`, Figure Contracts, and release artifacts. The `prepare-sprint`, `check-sprint`, and `merge-sprint` actions remain available only to replay historical Sprint-based projects and are not the default collaboration path.


## Local-first Python environments

The scripts scan existing Conda environments and select the environment with the
highest core-package coverage. On this machine that is `base` (Python 3.13.9).
Core verification is read-only. Missing extended packages are reported but do not
block baseline modeling, plotting, LaTeX, or PDF audit. The verified full target is
`math-modeling` (Python 3.13.x); `setup.ps1 -Tier extended` builds it in an
isolated prefix and never exposes another environment's `site-packages`. A
downloaded CPython source tree is not used as an interpreter or Conda prefix.

The selected environment and every package/command check are written to
`output/environment.json`.

## Research plotting MCP and CLI

The workspace has two pinned local rendering runtimes:

- Draw.io MCP `@drawio/mcp@1.5.0`: creates editable XML/Mermaid diagrams and opens them in draw.io. It is configured globally as `drawio`; icon-service requests are disabled.
- Mermaid CLI `@mermaid-js/mermaid-cli@11.16.0`: renders local Mermaid source to SVG, PNG, or PDF through the installed Microsoft Edge headless engine.

Example Mermaid export:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\render_mermaid.ps1 `
  -InputFile .\paper\figures\model-flow.mmd `
  -OutputFile .\paper\figures\model-flow.svg
```

MATLAB R2026a Update 4 is the main numerical, statistical, optimization, symbolic, and plotting CLI through `scripts/run_matlab.ps1`; the official MATLAB MCP binary remains optional because the local CLI is deterministic and already integrated with run manifests. Version, source, hash, and privacy decisions are recorded in `mcp.lock.yaml`.

## Configured mathematical-modeling skills

- `mathmodel-skill`: end-to-end CUMCM/MCM/ICM/electric-cup workflow, resumable state, rule checks, and submission gates.
- `math-modeling-solver`: problem decomposition, model selection, algorithms, and runnable optimization/prediction/evaluation templates.
- `math-modeling-paper`: Chinese/English contest paper structure, abstracts, validation, citations, and self-review.
- `modeling-paper-miner`: pinned-source discovery, A-D authenticity grading, content-vs-award deep-read gates, page evidence, PDF hashing, paper-code pairing, and MATLAB static screening.
- `skill_staging/visualization-design`: local combination Skill for evidence-form selection (`figure/table/text/none`), chart archetype and encoding decisions, Visual Intent, Figure Brief, and pre-render design review; it does not own claims or release state.
- `modeling-paper-studio`: evidence handoff, Figure Contract v2, template families, publication figures, XeLaTeX, PDF visual QA, and deep anonymous package audit.
- `matlab-build-chart`: MathWorks chart construction, `tiledlayout`, axes-first plotting, annotations, and `exportgraphics`.
- `matlab-solve-optimization`: MathWorks optimization formulation, solver selection, and result validation.
- `matlab-performance-optimizer`: MATLAB profiling, vectorization, preallocation, and memory guidance.
- `matlab-symbolic-math`: Symbolic derivation, equation solving, and symbolic-to-numeric conversion.
- Publication figures and document production reuse the existing `ccf-visual-composer`, `nature-figure`, `latex-document-skill`, and `pdf` skills.

The paper studio now includes a commit-pinned Nature-family figure-source index. It records nine DOI-verified papers, public repositories, exact plotting files, licenses, and transferable methods for forecasting, multi-objective comparison, robustness matrices, spatial/network figures, calibration, and selective rasterization:

- `corpus/top_journal_figure_code_index.csv`
- `corpus/top_journal_figure_methods.md`
- `skill_staging/modeling-paper-studio/references/top-journal-figure-code.md`

Repositories without an explicit license are indexed for method study only; their code is not copied into this workspace.

Pinned sources and audit evidence are recorded in `skills.lock.yaml` and `reports/github_skill_audit.md`. Newly installed global skills become discoverable on the next conversation turn.

The cluster intentionally keeps one orchestrator and does not install overlapping upstream suites wholesale. Patterns reviewed from Lupynow, MathModelAgent, and zhnnky are consolidated in `skill_staging/modeling-paper-studio/references/upstream-skill-patterns.md`: per-question handoffs, runnable baselines, risk probes, human decision points, frozen claims, scoped re-audits, and figure-template selection. This adds capability without introducing duplicate global names or a second state file.

Recommended prompts:

```text
Use $mathmodel-skill to start the 2026 CUMCM workflow and read contest.yaml.
Use $math-modeling-solver to propose a main model, baseline, validation plan, and runnable code.
Use $math-modeling-paper to write from verified experiment artifacts without hand-entering result numbers.
Use the local visualization-design skill to decide whether verified model output needs a figure, table, text, or no artifact, then prepare its Visual Intent and Figure Brief.
Use $matlab-build-chart with $modeling-paper-studio to create a Figure Contract and export PDF/SVG/PNG.
```

## MATLAB publication-figure workflow

MATLAB R2026a is pinned by `contest.yaml` and resolved through the shared `scripts/_matlab.ps1` helper. Registry, `MATLAB_ROOT`, machine PATH, and versioned installation directories are fallback discovery sources only. The launcher refreshes only the child process PATH; it does not duplicate permanent user PATH entries or select an incomplete uninstalled release.

Reusable chart code lives under `matlab/plotting/`:

- `applyModelingStyle.m` locks Chinese typography, print-safe colors, line weights, grids, and dark text on a white export background;
- `exportModelingFigure.m` exports vector PDF/SVG plus 400 dpi PNG;
- `demo_publication_figure.m` demonstrates a main-result chart with 95% confidence intervals and a parameter-sensitivity chart with a baseline marker.

Generated examples and evidence are in `output/_demos/matlab/`. The current R2026a installation passes graphics, Optimization Toolbox, Global Optimization Toolbox, Symbolic Math Toolbox, and Statistics and Machine Learning Toolbox checks. The smoke test executes `fitlm` and `fitctree` as well as checking that their functions are present.

## Evidence-grounded paper corpus

The retained base corpus contains the historical cards and 17 official 2024-2025 CUMCM display records. A separate 42-paper evidence program covers 24 CUMCM papers, 12 MCM/ICM papers, and 6 GMCM papers. It currently has 38 content-level deep reads and 4 key-page reviews; authenticity is A=6, B=12, C=24, with 14 award-verified deep reads. Two large public repositories are pinned by full commit and synchronized as read-only Git-tree manifests; repository names and filenames never count as award evidence.

```powershell
# Refresh pinned metadata only; no bulk code execution.
powershell -ExecutionPolicy Bypass -File .\scripts\corpus.ps1 -Action sync -Source all

# Index all 1457 upstream MATLAB paths without downloading or executing source.
powershell -ExecutionPolicy Bypass -File .\scripts\corpus.ps1 -Action scan-matlab `
  -TreeManifest .\corpus\upstream\sources\personqianduixue-math-model\8783d0d822f89f98aa6182dd933cc2e9f3e2ddce\git_tree.json `
  -Output .\corpus\upstream\matlab-index.json

# Rebuild the cross-schema card index and evidence report.
conda run -n base python .\scripts\build_corpus_index.py
conda run -n base python .\scripts\build_experience_report.py
```

Start with `corpus/experience_report.md` and `corpus/visual_style_guide.md`. Evidence for each claim is traceable through `corpus/cards/*.json`, `corpus/figure_inventory.csv`, and the page images named in those records. COMAP student-paper full text is indexed but not cached because the official resource page currently requires Mathmodels membership.

The corpus keeps public full text/page images separate from restricted-paper
indexes. New records must include a verified source URL, access level, and evidence
locator before they are counted as a structured exemplar. The current code-pair gate is intentionally `12/20`: the remaining eight candidates lack variable/output/hash evidence and are not inferred from directory co-location. The 12 modern recipes are deterministic and runnable. C-level deep reads support neutral modeling, writing, layout, and figure lessons only; they must not be called award-winning papers.
