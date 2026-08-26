---
name: visualization-design
description: "Design figure/table/text/none decisions and evidence-bound Figure Briefs for mathematical-modeling results before plotting, and review staged previews against the brief. Use for visualization design and staging only; do not use for formal Figure Contract promotion, manuscript-page visual QA, or release audits, which belong to modeling-paper-studio."
---

# Visualization Design

Turn a model output into the simplest defensible visual argument before plotting. Consume the current assembled `visualization` prompt packet for project, stage, scope, and transition semantics; do not restate or infer P/G-stage rules here.

## Ownership

- Own the `figure/table/text/none` decision, Visual Intent, Figure Brief, and design review of staged previews.
- Read solver-produced data handoffs; never change models, metrics, quality contracts, frozen claims, or competition state.
- Hand rendering to the selected Python or MATLAB backend. Keep every preview and render in the run's staging area.
- Hand formal Figure Contract promotion, manuscript-page inspection, and release QA to `modeling-paper-studio` and the root agent.
- Use `config/figure_style.yaml` and `journal-spectrum-v2` as the only palette and export authority. Pinned upstream sources are read-only methods; do not run their R, GUI, network, subprocess, or simulated-data workflows.

## Input Boundary

Always require a current `figure_data_manifest.yaml` with project-relative source paths, source hashes, declared fields, units, observation or replication unit, baseline, reader question, and evidence eligibility.

An exploratory or candidate handoff may produce a Visual Intent, a `DRAFT` or `REVIEWED` Figure Brief, and staged previews. It must not assert a frozen claim or become a formal Figure Contract.

A Formal or Paper Evidence Brief may become `APPROVED` only when all of the following upstream facts are current:

- the corresponding V7.2 model verification report has `status: READY` and matches the same project, question, run, and source manifest;
- the referenced semantic, metric, and algorithm-evidence contracts use `verification_profile: 1` and their recorded hashes have not drifted;
- the data handoff is eligible for contest evidence and traces only to Formal or qualified Paper Evidence.

If any prerequisite is absent, stale, or not ready, keep the Brief `DRAFT`, retain outputs in staging, and return the issue to the current packet owner. Do not reinterpret model-validation findings or copy quality-contract fields into the Figure Brief.

## Design Work

1. Inspect the data handoff and state the single reader question.
2. Decide whether a figure is better than a table, text statement, or no artifact.
3. For an exploratory decision, record a concise Visual Intent. For a figure, compare at most three archetypes and document the rejected alternatives.
4. Define mappings, units, baseline, denominator, uncertainty, visual hierarchy, labels, palette roles, physical size, backend, and read-only transformations in the Figure Brief.
5. Review the staged preview against the Brief. Color must have a redundant encoding; multi-panel layouts require an inseparability reason.
6. Produce a design/QA handoff for the root agent or paper studio. Never write `paper/figure_contracts.yaml`, `paper/figures/`, claims, or release files.

Plot only fields declared by the data manifest. Never paste result values into plotting code, infer significance from visual separation, or use upstream simulated data as contest evidence.

## Progressive References

Read only what the active task needs:

- For field definitions, lifecycle, or a handoff example, read [design-contract.md](references/design-contract.md).
- For choosing and rejecting an archetype, read [archetype-selection.md](references/archetype-selection.md).
- After a staged render exists, read [render-qa.md](references/render-qa.md).

Use [scripts/validate_handoff.py](scripts/validate_handoff.py) only for deterministic schema and local-provenance checks. It does not establish V7.2 model validity, approve a Brief, promote a Figure Contract, or replace the workspace workflow commands.
