# Literature Evidence Contract

Treat the four schemas as the authority:

- `literature_search_plan`: question-derived search problem and budget.
- `literature_search_receipt`: provider query, raw-result hash, normalized results, and deduplication record.
- `academic_reference_card`: verified metadata plus located technical evidence.
- `model_evidence_brief`: cross-paper comparison, model recommendation, experiment feedback, and citation handoff.

## Evidence depth

| Depth | Allowed use |
|---|---|
| `METADATA_ONLY` | Identity, discovery, and deduplication only |
| `ABSTRACT_SCREENED` | Relevance screening and candidate discovery |
| `TARGETED_READ` | Located model, formula, parameter, baseline, validation, or limitation support |
| `DEEP_READ` | Integrated assessment of formulation, implementation, evaluation, and boundary conditions |

Record every metadata snapshot and source document with a relative path and SHA-256. Compute the question-interface hash only from `schema_version`, `problem_id`, `question_id`, `source_problem`, and `problem`; exclude downstream decisions, evidence, paper handoffs, status, and the top-level `literature` block. For a targeted or deep read, preserve a PDF, HTML, or repository snapshot and at least one page, section, equation, table, figure, or appendix locator.

Treat command configuration as semantic input. The workflow implementation derives canonical artifact paths, current hashes, timestamps, and statuses before validation and writing.

## Extraction rules

- Separate what the paper states from what the current problem satisfies.
- Record units, data scale, split, baseline output class, and validation protocol.
- Record parameter values with their selection basis and applicability conditions.
- Record limitations, failure conditions, and non-transferable elements, not only the proposed method.
- Mark all reported external metrics with `not_project_evidence: true`.
- Treat code as inspected only after checking the repository; record a commit and license when present.

## Synthesis rules

For each candidate, cite card IDs by evidence role and compare matched versus mismatched conditions. Convert literature findings into a small Scratch experiment or risk probe. Do not let publication count or venue rank select the primary model automatically; the question interface, hard constraints, and project experiments decide.

Use `MODEL_REVIEW_SUGGESTED` when a credible paper exposes a severe contradiction or failure mode. This signal does not block Formal work through G4. Before G5, resolve the conflict, narrow the claim, document why it is not applicable, or replace the model recommendation.

## Citation handoff

Map every substantive statement to a `TARGETED_READ` or `DEEP_READ` card and its BibTeX key. Place citations in problem analysis, model selection, parameter basis, or model validation. Ensure every bibliography entry is cited and every cited key exists in a current card. Exclude PDFs, caches, receipts, cards, and internal briefs from G6 packages.
