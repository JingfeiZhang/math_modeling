# Relationship-to-Chart Guide

Choose the smallest visual form that makes the intended relationship legible. Document at most three candidates and why the others were rejected.

| Evidence relationship | Preferred form | Avoid or replace when |
|---|---|---|
| Ordered time / forecast | line; interval band if defined | bar chart implies discrete categories |
| Main model vs baseline | dot plot or compact grouped bars | many categories make bars unreadable; use a sorted table |
| Error or scenario distribution | box/violin with raw points | one observation per group; use dots and intervals |
| Parts summing to a whole | stacked bar | parts do not share a denominator; use grouped bars/table |
| Parameter sensitivity | line or heatmap | heatmap has no ordered axes or hides exact values |
| Resource/time occupancy | timeline or Gantt | dense intervals are better as a matrix |
| Sparse dependency network | node-link | dense graph becomes hairball; use adjacency matrix |
| Spatial variation | map | no meaningful geography, scale, or projection |
| Ranking / top-k | sorted horizontal bars or table | order is unstable or categories are too many |

## Decision questions

Answer these before drawing:

1. What should the reader conclude in one sentence?
2. Is the relation comparison, trend, distribution, composition, sensitivity, schedule, network, or spatial?
3. What is the observation or replication unit?
4. What is the denominator and baseline?
5. Can a table or sentence preserve the conclusion more exactly?
6. Which encoding remains understandable in grayscale?

## Modeling-specific cautions

- Prediction plots show observed, fitted, forecast, and interval semantics separately.
- Optimization plots include a comparable baseline and identify feasible versus infeasible solutions.
- Scheduling plots preserve time units and distinguish assignment from resource capacity.
- Sensitivity plots state the perturbation range and reference parameter; do not imply causality from a one-factor sweep.
- Heatmaps state whether color is a value, a rank, a residual, or a correlation and include a scale bar.
- Do not use a dual y-axis unless the two quantities share an explicit interpretive relationship and a single axis would hide the claim.

## Multi-panel rule

Default to one primary plotting area. Use panels only when each panel is a complementary part of one inseparable claim, shares comparable scales or a clearly stated change, and cannot be split into nearby figures without losing the comparison. Record the reason in `panel_justification`.

