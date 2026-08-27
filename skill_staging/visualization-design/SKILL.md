---
name: visualization-design
description: "Design figure/table/text/none decisions and evidence-bound Figure Briefs for mathematical-modeling results before plotting, and review staged previews against the brief. Use for visualization design and staging only; do not use for formal Figure Contract promotion, manuscript-page visual QA, or release audits, which belong to modeling-paper-studio."
---

# Visualization Design

Turn a model output into the **simplest defensible visual argument** before plotting. Consume the current assembled `visualization` prompt packet for project, stage, scope, and transition semantics; do not restate or infer P/G-stage rules here.

The academic objective is not “make a polished chart”. It is:

```text
Frozen / eligible evidence
→ reader question
→ evidence role
→ figure / table / text / none
→ visual encoding
→ conclusion-oriented caption
```

## Ownership

- Own the `figure/table/text/none` decision, Visual Intent, Figure Brief, and design review of staged previews.
- Read solver-produced data handoffs; never change models, metrics, quality contracts, frozen claims, or competition state.
- Hand rendering to the selected Python or MATLAB backend. Keep every preview and render in the run's staging area.
- Hand formal Figure Contract promotion, manuscript-page inspection, and release QA to `modeling-paper-studio` and the root agent.
- Use `config/figure_style.yaml` and the configured palette as visual authority. Pinned upstream sources are read-only methods; do not run their R, GUI, network, subprocess, or simulated-data workflows.

## Input Boundary

Always require a current `figure_data_manifest.yaml` with project-relative source paths, source hashes, declared fields, units, observation or replication unit, baseline, reader question, and evidence eligibility.

An exploratory or candidate handoff may produce a Visual Intent, a `DRAFT` or `REVIEWED` Figure Brief, and staged previews. It must not assert a frozen claim or become a formal Figure Contract.

A Formal or Paper Evidence Brief may become `APPROVED` only when all of the following upstream facts are current:

- the corresponding V7.2 model verification report has `status: READY` and matches the same project, question, run, and source manifest;
- the referenced semantic, metric, and algorithm-evidence contracts use `verification_profile: 1` and their recorded hashes have not drifted;
- the data handoff is eligible for contest evidence and traces only to Formal or qualified Paper Evidence.

If any prerequisite is absent, stale, or not ready, keep the Brief `DRAFT`, retain outputs in staging, and return the issue to the current packet owner. Do not reinterpret model-validation findings or copy quality-contract fields into the Figure Brief.

## Evidence Roles

A paper figure should primarily serve one of three academic roles:

1. **Result Figure** — answer “最终得到什么？”：预测轨迹、推荐方案、资源配置、Pareto 权衡、空间结果等；
2. **Validation Figure** — answer “为什么可信？”：样本外比较、误差分组、校准、敏感性、稳健性等；
3. **Mechanism Figure** — answer “为什么会得到这个结果？”：状态演化、影响关系、网络流、瓶颈、参数效应等。

A single figure may have secondary information, but should have one dominant reader question. If it cannot be assigned an evidence role, first consider table/text/none.

## Figure / Table / Text / None

Prefer:

- **table** when readers need exact values, rankings, parameter values, or compact multi-metric comparison;
- **figure** for trends, distributions, relations, uncertainty, spatial/network structure, schedules, failure modes or trade-offs;
- **text** for one to three key values that do not benefit from a visual artifact;
- **none** when the proposed artifact merely repeats a table, paragraph, or another figure.

A figure that cannot communicate information more efficiently than text/table should be deleted, even if visually attractive.

## Design Work

1. Inspect the data handoff and state **one primary reader question**.
2. State the intended evidence role: Result / Validation / Mechanism.
3. Decide whether a figure is better than a table, text statement, or no artifact.
4. For a figure, compare at most three archetypes and document the rejected alternatives; choose by relationship type, not familiarity.
5. Define mappings, units, baseline, denominator, uncertainty, visual hierarchy, labels, palette roles, physical size, backend, and read-only transformations in the Figure Brief.
6. Make the main model/result visually primary, baseline/reference visually neutral, and secondary candidates subordinate. Color must have a redundant encoding where distinction matters.
7. Multi-panel layouts require an inseparability reason: panels must jointly answer one reader question.
8. Review the staged preview against the Brief and ask whether the visual supports the frozen claim without exaggeration.
9. Produce a design/QA handoff for the root agent or paper studio. Never write `paper/figure_contracts.yaml`, `paper/figures/`, claims, or release files.

## Academic Visual Rules

- Plot only fields declared by the data manifest.
- Never paste result values into plotting code.
- Never infer statistical significance from visual separation alone.
- Never use upstream simulated/example data as contest evidence.
- Axes must expose variable meaning and unit when applicable.
- Baseline/reference must be identifiable whenever the claim is comparative.
- Uncertainty must be shown when it materially changes interpretation.
- Do not truncate axes, normalize, smooth, aggregate, log-transform or clip solely to make the result look stronger; such transformations must be declared and justified.
- Convergence curves demonstrate search behavior, not business/model validity or global optimality.
- ROC/PR, residual, heatmap, Pareto, map, network and Gantt are not “advanced” by themselves; use them only when they answer the reader question.
- Avoid 3D decoration, rainbow palettes, redundant legends, excessive annotations and duplicated table+bar-chart presentations.

## Caption Contract

A useful caption identifies the comparison/object, main encoding and important uncertainty/scenario context. It may state the evidence question, but the manuscript remains responsible for the substantive interpretation.

Bad:

> 问题二预测结果。

Better structure:

> 主模型与 seasonal-naive baseline 在滚动测试窗口的预测比较；阴影表示 95% prediction interval，峰值区间为主要剩余误差来源。

The caption cannot create a claim that is absent from Formal/Paper Evidence.

## Progressive References

Read only what the active task needs:

- For field definitions, lifecycle, or a handoff example, read [design-contract.md](references/design-contract.md).
- For choosing and rejecting an archetype, read [archetype-selection.md](references/archetype-selection.md).
- After a staged render exists, read [render-qa.md](references/render-qa.md).

Use [scripts/validate_handoff.py](scripts/validate_handoff.py) only for deterministic schema and local-provenance checks. It does not establish V7.2 model validity, approve a Brief, promote a Figure Contract, or replace the workspace workflow commands.
