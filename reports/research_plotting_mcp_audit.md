# 科研绘图 MCP 与 CLI 审计

审计日期：2026-08-01（GitHub API 快照）  
工作区：`D:\数学建模`

## 已配置

### Draw.io MCP

- 来源：[jgraph/drawio-mcp](https://github.com/jgraph/drawio-mcp)
- GitHub 快照：5,061 stars，Apache-2.0，2026-07-24 推送
- npm：`@drawio/mcp@1.5.0`
- 本地入口：`tools/mcp/drawio/node_modules/@drawio/mcp/src/index.js`
- Codex 名称：`drawio`
- 实际协议测试：初始化成功，服务端版本 `1.5.0`，返回 7 个工具：
  `open_drawio_xml`、`open_drawio_csv`、`open_drawio_mermaid`、
  `list_pages`、`get_page`、`set_page`、`search_shapes`
- 隐私设置：`DRAWIO_ICON_SERVICE_URL=off`。图表 XML 作为浏览器 URL fragment 传递；上游文档说明 fragment 不会随 HTTP 请求发送。Draw.io 页面代码仍会从 `app.diagrams.net` 加载，严格离线场景应使用本地 Draw.io Desktop 或自托管 viewer。
- 文件工具只处理 `.drawio`/`.xml` 页面文件；调用写入工具前仍需人工确认目标路径。

### Mermaid CLI

- 来源：[mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli)
- GitHub 快照：4,893 stars，MIT，2026-07-24 推送
- npm：`@mermaid-js/mermaid-cli@11.16.0`，`puppeteer@25.0.4`
- 本地入口：`tools/cli/mermaid/node_modules/@mermaid-js/mermaid-cli/src/cli.js`
- 浏览器：本机 Microsoft Edge，配置见 `tools/cli/mermaid/puppeteer.edge.json`
- 固定入口：`scripts/render_mermaid.ps1`
- 实测：同一个中文 Mermaid 流程图成功导出 SVG（14,593 bytes）、PNG（9,789 bytes）和 PDF（51,289 bytes）。
- 该 CLI 只读取本地 Mermaid 源文件并在本地浏览器渲染，不需要把图表提交到 Mermaid 在线编辑器。

## 已审计但未安装

### AntV MCP Chart

- 来源：[antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart)
- GitHub 快照：4,271 stars，MIT，2026-05-06 推送
- 支持 26+ 图表类型，适合快速探索性图表。
- 源码确认默认将完整图表参数 POST 到 `https://antv-studio.alipay.com/api/gpt-vis`，并返回远程图片 URL；这不适合含有竞赛原始数据或未公开结果的默认工作流。因此未安装。若以后部署 `GPT-Vis-SSR` 私有服务，可通过 `VIS_REQUEST_SERVER` 单独接入。

### MATLAB MCP Server

- 来源：[matlab/matlab-mcp-server](https://github.com/matlab/matlab-mcp-server)
- GitHub 快照：1,297 stars，MathWorks 官方仓库，2026-07-10 推送
- 最新 release：`v0.11.2`，Windows x64 资产 SHA-256：
  `f51a440c00f2031b317d90027fa554c5813b20e553f69484278e3abdf4c5a206`
- 官方文档支持 `--matlab-root`、`--initial-working-folder`、`--matlab-display-mode=nodesktop` 和 `--disable-telemetry=true`。
- 本次 GitHub release-assets 连接连续超时；官方 Go 源码构建也因当前 Go proxy 连接失败而未完成。没有把未下载的路径写入 Codex 配置。
- 2026-08-05 已迁移到 MATLAB R2026a Update 4；本地 CLI、Statistics、Optimization、Global Optimization、Symbolic 和论文图配方均通过。官方 MATLAB MCP 仍不接入主路径，因为现有 CLI 已能记录版本、命令、产物和哈希，且不引入第二套有状态执行服务。

### Jupyter MCP Server

- 来源：[datalayer/jupyter-mcp-server](https://github.com/datalayer/jupyter-mcp-server)
- GitHub 快照：1,233 stars，BSD-3-Clause，2026-07-31 推送
- 能力很强，但需要 Jupyter Server/Kernel 连接配置；当前工作区已有 MATLAB 本地绘图链和 Python 实验脚本，先不引入第二套有状态执行服务。

## 使用方式

```powershell
# Mermaid：论文级流程图/模型路线图
powershell -ExecutionPolicy Bypass -File .\scripts\render_mermaid.ps1 `
  -InputFile .\paper\figures\model-flow.mmd `
  -OutputFile .\paper\figures\model-flow.svg

# MATLAB：统计图、优化结果和敏感性分析
powershell -ExecutionPolicy Bypass -File .\scripts\run_matlab.ps1 `
  -Batch "addpath(genpath('D:/数学建模/matlab')); demo_publication_figure('D:/数学建模')"
```

Draw.io MCP 已写入 `C:\Users\Administrator\.codex\config.toml`。重启 Codex 后即可发现 `drawio`；Mermaid 和 MATLAB 是工作区 CLI，不需要作为 MCP 工具暴露。

## 维护规则

不要仅按 stars 自动升级。更新前重新检查上游提交、许可证、默认网络请求、文件访问范围、npm integrity/lockfile，并重新执行 `.audit/test_drawio_mcp.mjs` 与 Mermaid 三格式渲染测试。
