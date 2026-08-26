# Figure Design Handoff

Treat `config/schemas/figure_data_manifest.schema.json`,
`config/schemas/visual_intent.schema.json`, and
`config/schemas/figure_brief.schema.json` as the canonical field definitions. Start
from the matching files in `templates/workflow/`; do not invent aliases. Quote ISO
timestamps such as `"2026-08-11T08:00:00+00:00"` so YAML keeps them as strings.

## V7.2 approval prerequisite

The visualization schemas describe the design handoff; they do not prove that the
underlying model is valid. Before changing a Formal or Paper Evidence Brief to
`APPROVED`, confirm outside the Brief that the matching V7.2 model verification
report is `READY`, points to the same question/run/source manifest, and was built
from current `verification_profile: 1` semantic, metric, and algorithm-evidence
contracts. Do not invent Figure Brief fields for these checks. When the prerequisite
is not current, keep the Brief `DRAFT` and the render in staging.

## Required intent

`visual_intent.yaml` is the fast design record. Keep it short enough to write during model exploration:

```yaml
schema_version: 1
intent_id: intent-q1-candidate-001
question_id: Q1
run_id: candidate-001
source_data_manifest: experiments/C/Q1/candidate/candidate-001/figure_data_manifest.yaml
source_data_manifest_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
reader_question: "Does the calibrated forecast improve coverage over the baseline?"
evidence_role: main
artifact_decision: figure # figure | table | text | none
candidate_archetypes:
  - name: line-interval
    rationale: "Ordered time and defined uncertainty"
    rejection_reason: null
  - name: grouped-bar
    rationale: "Compact endpoint comparison"
    rejection_reason: "Bars hide the ordered trajectory"
required_encodings:
  x: timestamp
  y: forecast and interval
  group: method
  secondary: line style and marker
comparison: historical-rule
risks: ["interval may be mistaken for a confidence interval"]
paper_slot: paper/sections/question_1.tex
status: READY
contest_evidence_eligible: false
created_at_utc: "2026-08-11T08:00:00+00:00"
```

Scratch records may use `status: DRAFT` or `READY`; they are not formal evidence.

## Required brief

`figure_brief.yaml` is the design contract consumed by a renderer:

```yaml
schema_version: 1
brief_id: fig-q1-coverage
question_id: Q1
run_id: formal-001
source_data_manifest: experiments/C/Q1/formal/formal-001/figure_data_manifest.yaml
source_data_manifest_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
visual_intent: experiments/C/Q1/formal/formal-001/visual_intent.yaml
visual_intent_sha256: "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
claim_id: q1-coverage
core_conclusion: "The calibrated model maintains coverage closer to the target across horizons."
core_message: "Compare the main model and same-output baseline without adding manual values."
evidence_chain:
  - locator: experiments/C/Q1/formal/formal-001/coverage.csv:coverage
    sha256: "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
    fields: [horizon, method, coverage]
decision:
  artifact_type: figure
  archetype: prediction-interval
  alternatives:
    - {kind: grouped-bar, rejected_reason: "It hides the ordered horizon response."}
  rationale: "A line on the ordered horizon axis exposes calibration drift."
encodings:
  x: horizon
  y: coverage
  color: method
  marker: method
  facet: null
  units: {horizon: min, coverage: proportion}
visual_hierarchy:
  primary_evidence: main_model
  secondary_context: baseline
  deemphasized: reference_target
panel_map: [{panel: main, role: primary, subclaim: q1-coverage}]
labels:
  strategy: direct
  collision_check_required: true
  annotations: []
legend: "Use an external legend only if direct labels collide."
palette_id: journal-spectrum-v2
color_encoding:
  - {role: main_model, meaning: calibrated model, secondary_encoding: "solid line + circle"}
  - {role: baseline, meaning: historical rule, secondary_encoding: "dashed line + square"}
backend: python
target_size_profile: contest-body
final_width_mm: 158
min_font_pt: 8
source_data: [experiments/C/Q1/formal/formal-001/coverage.csv]
source_script: src/plotting/plot_q1_coverage.py
source_script_sha256: "89abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567"
outputs:
  pdf: experiments/C/Q1/formal/formal-001/figure-staging/fig-q1-coverage/outputs/fig-q1-coverage.pdf
  svg: experiments/C/Q1/formal/formal-001/figure-staging/fig-q1-coverage/outputs/fig-q1-coverage.svg
  png: experiments/C/Q1/formal/formal-001/figure-staging/fig-q1-coverage/outputs/fig-q1-coverage.png
  png_dpi: 400
baseline: historical-rule
axes: [{variable: horizon, unit: min}, {variable: coverage, unit: proportion}]
caption: "Coverage by forecast horizon for the calibrated model and same-output baseline."
statistics: ["mean coverage by forecast window; empirical interval"]
statistics_report:
  sample_size: "n forecast windows"
  center: mean
  interval: empirical-quantile
  test: not-applicable
  multiplicity: not-applicable
data_integrity:
  source_hashes:
    - {path: experiments/C/Q1/formal/formal-001/coverage.csv, sha256: "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"}
  transformation: "read-only groupby(method,horizon)"
  manual_values_forbidden: true
label_strategy: {mode: direct, collision_checked: false, justification: "Reduce legend lookup."}
rasterized_layers: []
review_risks: ["do not compare intervals as significance tests"]
read_only_transformations: ["read-only groupby(method,horizon)"]
status: APPROVED
qa_expectations: ["PDF, editable-text SVG, and 400 dpi PNG pass final-size QA."]
approval:
  decision_id: visual-q1-coverage
  approved_by: root-agent
  approved_at_utc: "2026-08-11T08:10:00+00:00"
contest_evidence_eligible: true
created_at_utc: "2026-08-11T08:05:00+00:00"
```

For `table`, `text`, or `none`, retain the decision, source fields, units, and rationale in `visual_intent.yaml`; do not create a Figure Brief merely to satisfy a figure count. `claim_id` may be null only for non-formal work or an eligible diagnostic that does not assert a frozen result claim. Candidate briefs remain `DRAFT` or `REVIEWED`; approval requires the V7.2 prerequisite above.

## Lifecycle

```text
DATA_READY → INTENT_READY → BRIEF_READY → DESIGN_APPROVED
→ RENDERED → QA_PASSED → CONTRACT_READY
```

Derive status from the artifacts. Any source, parent Formal manifest, code, input, or design hash drift makes the handoff `STALE`. A promoted contract must carry `design_handoff` paths and hashes; it must not duplicate frozen result values.

Run `scripts/validate_handoff.py` with the workspace Python environment that provides PyYAML and jsonschema. Pass `--root` when automatic workspace discovery is not possible. The validator checks schema shape and local file provenance only; it does not inspect model-verification readiness, approve a Brief, inspect manuscript pages, or replace the formal workflow.
