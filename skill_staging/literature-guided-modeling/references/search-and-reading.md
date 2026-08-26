# Search and Reading Rules

Read this reference before planning, searching, screening, or targeted reading. The current assembled literature packet supplies the budget and stopping conditions.

## Search Inputs

Start from the current Qx interface: domain object, mathematical task, required output, data conditions, dominant constraints, primary metric, and unit. If the packet authorizes the question's quality-contract references, inspect them read-only and list only gaps that literature can inform.

Do not let literature redefine a problem requirement. A paper can suggest a model, validation method, or probe; the statement and project contracts decide what the current problem requires.

## Query Construction

Use two primary query families:

1. Scenario-task: domain object + required output + uncertainty, evaluation, or deployment condition.
2. Method-constraint: model family or mathematical task + dominant constraint + data condition.

Add one focused verification query only for a named gap:

- Requirement coverage: required output or metric + task + evaluation protocol.
- Known-answer case: analytical solution, exact benchmark, exhaustive small instance, limiting case, or solver-verification example.
- Baseline or challenger: comparative benchmark, simple same-output baseline, alternative model family, or ablation.
- Invariant: feasibility, conservation, boundary, dimensional consistency, nonnegativity, monotonicity, or interface validation.
- Prediction: rolling-origin or grouped validation, leakage prevention, residual bias, interval coverage, or calibration.
- Optimization: exact small-instance comparison, lower or upper bound, optimality gap, feasibility rate, convergence, or multi-seed stability.
- Mechanistic model: dimensional analysis, conservation, boundary and initial conditions, limiting behavior, identifiability, calibration, or sensitivity.
- Evaluation or ranking: indicator direction, normalization sensitivity, weight perturbation, leave-one-indicator-out stability, or simple ranking baseline.

Stop according to the packet even if evidence remains incomplete. Do not broaden the search merely to accumulate papers.

## Source and Identity

Use CrossRef, OpenAlex, and arXiv for discovery and stable identifiers. Use Semantic Scholar for complementary discovery. Treat Google Scholar, CNKI, and Wanfang as manual supplements whose metadata must be verified against a publisher, DOI registry, repository, or another authoritative record.

Accept only journal articles, conference papers, preprints, and theses. Exclude contest papers, textbooks, quick-reference cards, blogs, marketing pages, generated summaries, and unsourced method lists from academic model evidence.

Deduplicate by normalized DOI. Without a DOI, compare normalized title, first author, and year. Preserve provider identifiers in the search receipt and record metadata conflicts instead of silently choosing a value.

## Screening

Keep a packet-bounded shortlist and rank it by:

1. Same task and output class.
2. Similar hard constraints, data conditions, and validation setting.
3. Implementability within the current contest context.
4. Comparable baseline, challenger, or verification design.
5. Located formulas, algorithm details, benchmark cases, or code.
6. Source quality and recency.

Do not select a paper because it reports the best metric. A result under a different split, output class, unit, constraint, or denominator is not evidence of fit.

## Targeted Reading

Read the smallest section that can support the pending decision:

- Model family: abstract, end of introduction, related work, and method overview.
- Formula or algorithm: method section, equations, pseudocode, and appendix.
- Parameter: experimental setup and parameter analysis.
- Baseline, challenger, or metric: evaluation protocol, ablation, benchmark, and result-definition text.
- Oracle or invariant: analytical derivation, benchmark definition, proof, solver cross-check, boundary analysis, or supplementary validation.
- Limitation: discussion, conclusion, failure cases, sensitivity, and external-validity notes.
- Code: repository metadata, pinned commit, license, inputs, outputs, and reproduction notes.

Use `TARGETED_READ` only after inspecting full text and recording a precise locator. Use `DEEP_READ` when formulation, implementation, evaluation, and limitations have all been checked. Abstract-only knowledge never supports an exact formula, parameter, algorithm step, validation prescription, or performance statement.
