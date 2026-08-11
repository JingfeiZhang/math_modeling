# CUMCM 论文-代码配对与现代配方审计

## 结论

- 固定来源：`personqianduixue/Math_Model@8783d0d822f89f98aa6182dd933cc2e9f3e2ddce` 的 `2-1国赛题目+论文`。
- 18 个同目录候选折叠为 17 篇唯一论文；其中 12 个满足正文-代码证据要求，5 个仍为 `candidate_only`。
- 20 对目标真实缺口为 8；没有用重复 PDF 或仅同目录记录补数。
- 静态审查 32 个目录副本 / 31 个唯一 MATLAB 文件，共 9 条提示；高风险项 0 条。
- 12 个现代配方全部隔离运行成功，且相同种子下指标与输出哈希 12/12 一致。

## 配对证据

| 候选 | 关系 | 可信 | PDF页 | 代码文件 | 片段 | 方法 | 变量 |
|---|---:|:---:|---:|---:|---:|---:|---:|
| `cumcm-2012-a285` | `candidate_only` | 否 | 41 | 1 | 0 | 0 | 0 |
| `cumcm-2012-b077` | `candidate_only` | 否 | 34 | 2 | 0 | 0 | 0 |
| `cumcm-2012-b113` | `candidate_only` | 否 | 18 | 2 | 0 | 0 | 1 |
| `cumcm-2012-b149` | `exact` | 是 | 30 | 2 | 6 | 0 | 13 |
| `cumcm-2013-a056` | `strong_partial` | 是 | 35 | 2 | 0 | 2 | 3 |
| `cumcm-2013-a117` | `exact` | 是 | 46 | 2 | 12 | 2 | 22 |
| `cumcm-2013-b201` | `exact` | 是 | 32 | 2 | 12 | 0 | 16 |
| `cumcm-2013-b254` | `exact` | 是 | 33 | 2 | 12 | 0 | 8 |
| `cumcm-2014-a012` | `exact` | 是 | 32 | 1 | 5 | 1 | 4 |
| `cumcm-2014-a305` | `exact` | 是 | 36 | 2 | 12 | 0 | 10 |
| `cumcm-2014-a377` | `exact` | 是 | 39 | 2 | 12 | 0 | 24 |
| `cumcm-2014-a499` | `exact` | 是 | 28 | 2 | 12 | 1 | 5 |
| `cumcm-2014-b009` | `exact` | 是 | 25 | 2 | 12 | 1 | 5 |
| `cumcm-2014-b013` | `candidate_only` | 否 | 26 | 2 | 0 | 0 | 0 |
| `cumcm-2014-b261` | `supported_partial` | 是 | 25 | 2 | 0 | 0 | 2 |
| `cumcm-2014-d026` | `exact` | 是 | 23 | 1 | 5 | 0 | 0 |
| `cumcm-2016-xipoxitong-master` | `candidate_only` | 否 | 39 | 2 | 12 | 0 | 24 |

`exact` 表示 PDF 中可定位至少两处源代码行；`strong_partial` 与 `supported_partial` 需要队号/控制号匹配，并有方法、变量、文件名或标签等额外对应。仅同目录一律不计可信。

## 静态风险

- `session_mutation`：9 条。
- 原始 MATLAB 执行状态：`not_executed`。
- 当前命中均为 `clear all` / `close all` 会话修改；没有发现删除、系统命令、网络或动态执行。

## 可运行配方

| 配方 | 来源配对 | 首次运行 | 二次哈希复现 | 输出 |
|---|---|:---:|:---:|---|
| `cellular-traffic` | `cumcm-2013-a117` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `folding-table-geometry` | `cumcm-2014-b009` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `folding-table-shape-scan` | `cumcm-2014-b261` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `fragment-global-matching` | `cumcm-2013-b254` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `fragment-row-matching` | `cumcm-2013-b201` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `lunar-descent-control` | `cumcm-2014-a305` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `normal-uncertainty-monte-carlo` | `cumcm-2014-a012` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `ode-parameter-sensitivity` | `cumcm-2014-a499` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `solar-tilt-sensitivity` | `cumcm-2012-b149` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `storage-slot-sizing` | `cumcm-2014-d026` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `traffic-capacity-ga` | `cumcm-2013-a056` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |
| `trajectory-angle-scan` | `cumcm-2014-a377` | 通过 | 通过 | results.json, series.csv, figure.png, figure.svg, figure.pdf |

每个 `corpus/recipes/<id>/run_report.json` 记录 Python/NumPy/Matplotlib 版本、随机种子、输入与输出 SHA-256、指标及隔离声明。所有配方使用受控合成输入，只复用数学结构，不宣称复现论文数值。

## 仍有缺口

- This pinned CUMCM subtree contains only 17 unique PDF candidates with MATLAB in the same team-level directory, so 20 trusted pairs cannot be produced honestly from this scope.
- Five canonical candidates lacked sufficient page-to-code overlap and remain candidate_only.
- Auxiliary data files are metadata-only in this pass; no unreviewed upstream data or MATLAB was executed.
- Several historical PDFs contain malformed cross-reference pointers; pypdf recovered text with warnings, so visible page locators remain the primary evidence.
- The content-addressed download area may contain unreferenced objects from an interrupted raw download; download_manifest.json is the authoritative allowlist.

## 复核入口

- `corpus/reports/code-recipe-mining-artifacts/download_manifest.json`：固定提交、blob SHA 与下载 SHA-256。
- `corpus/reports/code-recipe-mining-artifacts/pair_evidence.json`：逐页正文-代码对应证据。
- `corpus/reports/code-recipe-mining-artifacts/matlab_static_scan.json`：静态风险。
- `corpus/reports/code-recipe-mining-artifacts/recipe_execution.json`：首次隔离运行。
- `corpus/reports/code-recipe-mining-artifacts/recipe_determinism.json`：二次复现。
