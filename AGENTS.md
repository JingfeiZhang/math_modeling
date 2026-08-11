# Mathematics Modeling Workspace

## Workflow ownership

- Use `mathmodel-skill` as the only owner of competition stages, recovery state, official-rule checks, and human decisions.
- Use `math-modeling-solver` for problem decomposition, model selection, executable baselines, algorithms, experiments, and robustness.
- Use `math-modeling-paper` for contest-paper structure, section drafting, model-validation prose, and manuscript review.
- Use `modeling-paper-studio` for evidence handoff, Figure Contracts, publication figures, XeLaTeX, PDF visual QA, and submission audits.
- Use `modeling-paper-miner` for pinned-source discovery, authenticity grading, PDF/OCR evidence cards, deduplication, and paper-code pairing. It never owns contest state.
- Use the installed MATLAB skills only for MATLAB charts, optimization, symbolic work, and performance work. Do not create a second workflow state file.
- Use journal-spectrum-v2 for all self-authored data colors. The categorical order is fixed as #CC247C, #E95351, #F7A24F, #FBEB66, #4EA660, #79CAFB, #5292F7, #AA77E9; semantic roles must use the shared mapping in config/figure_style.yaml.
- Do not introduce a new data color in Python, MATLAB, LaTeX, Origin, or an MCP output. Text, axes, grids, fills, and backgrounds may use only the registered neutral colors.
- Default to one figure with one primary plotting area. Use multi-panel figures only when complementary evidence cannot be separated, and record the reason in the formal Figure Contract.
- Treat `TingxiYu/academic-figure-skill@1df9940dd01ac939f072b12fe28d6353b79b90f9` as a pinned read-only method source. Do not run its simulated-data, R, GUI, network, or subprocess scripts and do not adopt its external palettes.
- Upstream preview data and simulated statistics are never contest evidence. Formal figures must read frozen project evidence and export PDF, editable-text SVG, and 400 dpi PNG at the declared final size.

## Required sequence

1. For isolated projects, read `projects/<competition>/<year>/contest.yaml` and shared `config/workflow.yaml`. The root `contest.yaml` is legacy compatibility only.
2. Select every isolated project explicitly with `scripts/workflow.ps1 -Project <project-id> ...`; never infer an active project from the current directory or a global pointer.
3. Before the problem is released, run only preflight, corpus, template, and tooling work. Do not create `state/decision_log.json` or formal Q1/Q2 artifacts.
4. After a real problem file is supplied, initialize through `scripts/workflow.ps1 -Project <project-id> -Action initialize`.
5. For each real subproblem, maintain one question manifest, executable main model, comparable baseline, at most one conditional fallback, risk probes, run manifests, robustness evidence, frozen claims, and Figure Contract links.
6. Permit manuscript claims and figures to use only frozen evidence. Treat changed evidence hashes as an invalidation that requires review and refreezing.
7. Build, audit, and package only through the workspace scripts. Fix the earliest failed G0-G6 gate before continuing.

## Project isolation

- Shared assets live only at the workbench root: environments, Skills, corpus, templates, workflow code, and the journal-spectrum-v2 palette.
- Mutable competition artifacts live only under the registered project root: problem files/data, runners, experiments, claims, paper, output, state, sprints, and logs.
- Project ids and roots are registered in `config/projects.json`; roots must be unique and remain under `projects/`.
- Never read another project's data or evidence into a run unless it is explicitly copied into the target project and recorded as an external source with a hash.
- Huashu Cup inherits the CUMCM format/rule profile when no event-specific instruction exists. Explicit Huashu Cup rules always override inherited values.
- Root-level artifacts remain available only for backward-compatible tests and demos; new contests must use project mode.
- Root-level `paper/`, `problems/`, `experiments/`, `results/`, and `figures/` are legacy-demo compatibility areas. Do not place new contest artifacts there.
- Workbench-level generated artifacts use `output/_verification/`, `output/_demos/`, and `output/_archive/`; operational reports and release files remain at `output/` root.
- Use `scripts/workspace.ps1 -Action inspect|preview|normalize|verify` to inspect or normalize layout. Normalization moves only allow-listed generated artifacts and never deletes files or enters `projects/`.

## Evidence rules

- Never enter an unverified number manually in the paper, caption, or chart script.
- Every run must record the command, environment, seed, code/data hashes, outputs, metric definitions, units, and runtime.
- Every figure must record a claim id, evidence locator, baseline, axes with units, source script, caption, and PDF/SVG/PNG exports.
- Baselines must produce the same class of output as the main model. A random result or diagnostic line is not a baseline.
- A fallback is optional, limited to one per subproblem, and must have an explicit activation trigger.
- Mechanical checks belong in scripts. Ask the user only when ambiguity or a tradeoff changes the model, claim scope, or fallback decision.

## Multi-agent collaboration

- Enable parallel agent collaboration by default for all workspace tasks, including formal competition stages, whenever the work contains at least two independent useful workstreams. Do not require the user to request multi-agent mode again.
- Use lightweight delegation rather than a sprint workflow. Do not require sprint manifests, formal task packages, deadlines, or target-gate fields merely to start worker agents.
- This workspace policy overrides the installed `mathmodel-skill` requirement to dispatch multi-agent work through `references/multi-agent-sprint.md`. Continue using `mathmodel-skill` for stage ownership, recovery state, official rules, and human decisions, but use the lightweight delegation rules in this section for agent coordination.
- Do not impose a workspace-level worker-count limit. Use as many workers as the current runtime exposes and the task can usefully support. Give each worker a concise objective, bounded read scope, unique write scope when it edits files, and expected output. Pin input hashes only when a worker consumes mutable or formal evidence.
- The root agent coordinates the work, resolves conflicts, verifies outputs, and performs the final integration. The root agent alone may modify `state/decision_log.json`, frozen claims, `paper/main.tex`, formal `paper/figure_contracts.yaml`, or submission packages.
- Solver agents write only assigned experiment folders and claim proposals. Figure/writer agents write only staging artifacts. Reviewers write review JSON only. Workers may perform read-only analysis anywhere within the selected project.
- Reject stale formal evidence, scope violations, or failed gates. Retry or reassign only the affected subtask, then let the root agent merge.
- For a genuinely atomic task that cannot benefit from parallel work, the root agent may complete it directly instead of creating idle workers.

## Upstream use

- Keep Lupynow's installed solver and paper skills pinned and unmodified.
- Learn stage handoffs and composite-figure layouts from `jihe520/MathModelAgent`, but never use its simulated template data as contest evidence.
- Learn per-question gates, baselines, risk probes, decision ledgers, and frozen-number handling from `zhnnky329/MathModeling-skills`, without installing its overlapping global skill names.
- Treat `zhanwen/MathModel@cd5be91735ebf11d5ee52eb170e86a6d07131977` and `personqianduixue/Math_Model@8783d0d822f89f98aa6182dd933cc2e9f3e2ddce` as pinned read-only corpus/code sources. Do not execute unscreened MATLAB files.
- A filename or community description cannot establish an award. Require official evidence or a verifiable team/problem/result match for A/B grading.
- Verify competition identity from the rendered cover before counting a paper. The `zhanwen` `国赛论文` tree is primarily GMCM; papers whose cover identifies 中国研究生/全国研究生数学建模竞赛 remain GMCM candidates and are quarantined from CUMCM totals.
- Official image-page exhibits may be assembled into a local review PDF, but the page-image URLs, hashes, and official locator remain the authoritative provenance.
