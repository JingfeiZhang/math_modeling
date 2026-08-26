# Render and Handoff QA

## Before rendering

- Confirm the manifest is from the intended question and run, with a current SHA-256.
- Resolve every field and unit from the manifest; reject manual numeric constants for formal evidence.
- Confirm the baseline, denominator, threshold, replication unit, and uncertainty definition.
- Confirm `palette_id: journal-spectrum-v2` and semantic role mappings from `config/figure_style.yaml`.
- Confirm final width, height bounds, minimum font size (8 pt or the event rule if stricter), and backend.

## Staging outputs

Render into the run's `figure-staging/<figure-id>/outputs/`, never directly into `paper/figures/`. Formal and approved Paper Evidence outputs are:

```text
<figure-id>.pdf
<figure-id>.svg  # editable text, not a raster wrapper
<figure-id>.png  # 400 dpi
figure_qa.json
```

Scratch previews may be PNG only and are never paper evidence.

## Automated checks

Record pass/fail and evidence in `figure_qa.json`:

- source files and field locators exist and hashes match;
- all axes have labels and units where applicable;
- scale, zero/reference, baseline, and interval semantics are explicit;
- no NaN-only series, accidental sorting, duplicated categories, or hidden missing values;
- PDF/SVG/PNG exist, have declared dimensions, and PNG metadata reports 400 dpi;
- SVG contains text elements and is not an embedded bitmap only;
- no clipping, overlapping annotations, legend collisions, or unreadable tick labels;
- line styles and markers remain distinguishable in grayscale and for common color-vision deficiencies;
- no unregistered colors, gradients, 3-D effects, chartjunk, or unexplained dual axes;
- caption plan states object, conditions, comparison, and conclusion.

## Manual review

Open the staged PDF and inspect the figure at its declared final size. Verify that the primary evidence is visually dominant, reference/background layers are subdued, labels do not collide, and the figure can be understood without reading plotting code. Defer surrounding-page flow, float placement, caption separation, and manuscript citation checks to `modeling-paper-studio`.

## Studio handoff conditions

This Skill stops after staged-preview review and a design/QA handoff. Send only an approved, unchanged Brief with passing staged QA and qualified upstream evidence to `modeling-paper-studio`. The root agent and studio own Figure Contract promotion, manuscript-page inspection, and release QA. If the upstream V7.2 model verification report or any referenced quality-contract/data hash is no longer current, keep the handoff out of formal promotion and return it to the current packet owner.
