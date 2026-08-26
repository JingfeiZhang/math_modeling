# Literature Evidence Contract

Read this reference before Model Evidence Brief synthesis or citation handoff.

## Canonical Artifacts

Treat the four schemas as authoritative:

- `literature_search_plan`: question-derived search problem and packet-bounded search plan.
- `literature_search_receipt`: provider query, raw-result hash, normalized results, and deduplication record.
- `academic_reference_card`: verified metadata plus located technical evidence.
- `model_evidence_brief`: cross-paper comparison, provisional model recommendation, experiment proposals, and citation handoff.

## Evidence Depth

| Depth | Allowed use |
|---|---|
| `METADATA_ONLY` | Identity, discovery, and deduplication only |
| `ABSTRACT_SCREENED` | Relevance screening and candidate discovery |
| `TARGETED_READ` | Located model, formula, parameter, baseline, challenger, validation, oracle, invariant, or limitation support |
| `DEEP_READ` | Integrated assessment of formulation, implementation, evaluation, and boundary conditions |

Record each metadata snapshot and source document with a project-relative path and SHA-256. For a targeted or deep read, preserve a PDF, HTML, or repository snapshot and at least one page, section, equation, table, figure, appendix, or pinned-code locator.

## Extraction

- Separate what the paper states from what the current problem satisfies.
- Record units, data scale, split, output class, denominator, baseline, challenger, and validation protocol.
- Record parameters with their selection basis, applicability conditions, and uncertainty.
- Locate analytical limits, benchmark instances, exact comparisons, invariants, convergence evidence, or robustness designs when they inform a named verification gap.
- Record limitations, failure conditions, and non-transferable elements, not only the proposed method.
- Mark every reported external metric with `not_project_evidence: true`.
- Treat code as inspected only after checking the repository; record a commit and license when present.

The literature chain may propose a known-answer fixture, invariant check, model comparison, or robustness probe. Only the solver and project experiment chain can execute it and produce project evidence.

## Synthesis

For each candidate, cite card IDs by evidence role and compare matched versus mismatched conditions. The brief should distinguish:

- a same-output baseline from a diagnostic or random reference;
- the provisional main-model recommendation from a lightweight challenger;
- a challenger from the single conditional fallback;
- paper-reported validation from validation actually run on project data;
- general applicability conditions from the current problem's verified conditions.

Where useful, map requirement-coverage gaps to located methods and proposed checks. Include an oracle or small-instance proposal, relevant invariants, task-specific validation, sensitivity or robustness probes, rejection triggers, and a challenger-omission rationale when no meaningful challenger is found.

Do not let publication count, venue rank, or an external performance number select the model automatically. The question interface, fixed inputs, hard constraints, comparable project experiments, and human decisions determine selection. A credible contradiction produces `MODEL_REVIEW_SUGGESTED`; resolve it during the current packet's review path without changing a model or claim from this skill.

## Citation Handoff

Map every substantive external statement to a `TARGETED_READ` or `DEEP_READ` card and its BibTeX key. Place citations only where the manuscript workflow requests model background, selection basis, parameter basis, or validation provenance. Ensure each bibliography entry is cited and each cited key exists in a current card.

Exclude source PDFs, caches, receipts, cards, briefs, textbook quick-reference cards, and their internal instructions from submission and release artifacts. None of these artifacts is Formal evidence or a project claim.
