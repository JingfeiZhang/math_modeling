---
name: visualization-design
description: "Design evidence-grounded charts for mathematical-modeling contest papers before plotting. Use when model or algorithm output needs a figure, table, or no-figure decision; when selecting chart types and visual encodings; when preparing a Figure Brief; or when checking a rendered figure before it enters a Figure Contract."
---

# Visualization Design

Turn model output into a defensible visual argument before writing plotting code. The skill owns the design decision and handoff artifacts; it does not own contest state, frozen claims, the primary model, or the final release audit.

## Boundaries

- Use `mathmodel-skill` for contest stages and `state/decision_log.json`.
- Use `math-modeling-solver` for models, baselines, experiments, and source data.
- Use `modeling-paper-studio` for formal Figure Contracts, rendering, paper integration, and G5/G6 audits.
- Use `matlab-build-chart` or the project plotting backend only after the design is approved.
- Treat `config/figure_style.yaml` and `journal-spectrum-v2` as the only palette and export authority. Never import an external palette, default DPI, or external global workflow.
- Read `config/visualization_sources.yaml` only when provenance for an adopted design rule is needed; keep every listed repository at its pinned commit and in read-only mode.
- Do not run external R, GUI, network, simulated-data, or subprocess scripts. The pinned upstream skills are read-only method sources.

## Design Pipeline

1. **Inspect the data handoff.** Read the solver-produced `figure_data_manifest.yaml`. Confirm the question, run level, evidence eligibility, source fields, units, observation unit, baseline, and intended reader question. Reject absolute source paths, missing units, unverifiable hashes, or manually entered result values.
2. **Choose the evidence form.** Decide among `figure`, `table`, `text`, and `none`. Prefer a table or a sentence when exact values or a single comparison are clearer than a plot. A figure must answer one primary reader question.
3. **Create a lightweight intent.** For Scratch output, write `visual_intent.yaml` with the reader question, evidence role, up to three candidate chart types, provisional encodings, baseline, units, risks, paper slot, and source-manifest hash. Scratch intent is exploratory and never becomes a claim or formal Figure Contract.
4. **Create a complete brief.** For Candidate, Formal, or Paper Evidence output, write `figure_brief.yaml`. Record candidate rejections, the final archetype, mappings and units, statistics, visual hierarchy, panel justification, labels, palette roles, physical size, backend, export formats, and QA checks. Keep transformations read-only and reproducible.
5. **Review the design.** Check that the chosen visual is the simplest truthful encoding, that axes and baselines are comparable, that uncertainty is visible when relevant, and that color is not the only encoding. A multi-panel figure requires a written reason that the evidence cannot be split without losing the argument.
6. **Render only into staging.** Plot from manifest-declared fields using Python or MATLAB. Do not paste numbers into plotting code. Candidate previews may be raster-only; Formal and approved Paper Evidence render PDF, editable-text SVG, and 400 dpi PNG at the declared size.
7. **Run render QA.** Check source hash, dimensions, units, labels, legend, direct labels, clipping, overlap, line/marker readability, grayscale and color-vision redundancy, and required output files. Save `figure_qa.json` beside staged outputs.
8. **Promote through the paper studio.** Only the root agent may update `paper/figure_contracts.yaml`. Attach the manifest, intent, brief, and QA paths plus their hashes under `design_handoff`; then let the existing Figure Contract and G5/G6 checks decide release eligibility.

## Chart Selection Heuristics

Start from the relationship, not the preferred library:

- **Trend or forecast over ordered time:** line with observed/predicted distinction and an interval band when available.
- **Model/baseline comparison:** dot plot or compact grouped bars; sort by a meaningful metric and keep the baseline visible.
- **Distribution, error, or scenario spread:** box/violin plus raw points when sample size permits; state the unit of replication.
- **Composition or resource allocation:** stacked bars only when parts sum to a meaningful whole; otherwise use grouped bars or a table.
- **Sensitivity or parameter response:** line or heatmap with explicit parameter units and a reference setting.
- **Schedule, assignment, or interval occupancy:** timeline/Gantt or matrix; preserve the time/resource semantics.
- **Network or dependency structure:** node-link only for a sparse interpretable graph; use a matrix for dense connectivity.
- **Spatial result:** map only when geography is part of the question and the projection/scale is available.

Use small multiples only for genuinely repeated comparisons. Avoid 3-D, dual axes, pie charts, decorative flows, unexplained heatmaps, and plots with more categories than a reader can scan. Use direct labels where they reduce legend lookup. Keep one primary plotting area by default.

## Evidence and Color Rules

- Bind every plotted field to a source locator and SHA-256. Derived summaries must declare the read-only aggregation and preserve the observation unit.
- State the baseline, denominator, threshold, and uncertainty definition in the brief and caption plan.
- Use the semantic roles in `config/figure_style.yaml` (`main_model`, `baseline`, `improved_model`, `risk_or_error`, and so on). Add line style, marker, ordering, or direct labels as a second encoding.
- Keep axes in physical units, show zero or a justified reference, and never truncate an axis to exaggerate an effect without an explicit annotation.
- Do not infer significance from visual separation. Report the metric, interval, test, or sensitivity definition that supports the prose claim.

## Paper Evidence Reuse

Paper Evidence may add diagnostics, sensitivity, mechanism, or figure-support summaries only when it reuses the Formal input, code, environment, seed, solver, and parameters. It may create a new handoff and brief but may not mutate the primary model. Return `REOPEN_REQUIRED` and reopen only the affected question if the parent Formal hash changes, a main metric or unit drifts, a hard constraint fails, model selection changes, or deterministic replay fails.

## References

Read only the reference needed for the current task:

- [design-contract.md](references/design-contract.md): handoff fields, lifecycle, and examples.
- [archetype-selection.md](references/archetype-selection.md): relationship-to-chart decision table and rejection criteria.
- [render-qa.md](references/render-qa.md): staging, export, visual, and evidence QA checklist.

Use [scripts/validate_handoff.py](scripts/validate_handoff.py) for deterministic local checks before invoking project workflow commands. It validates shape and provenance only; it does not approve a claim or replace G3/G4/G5/G6.
