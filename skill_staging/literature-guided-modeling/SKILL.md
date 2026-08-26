---
name: literature-guided-modeling
description: "Plan, verify, read, and synthesize academic literature for a named mathematical-modeling contest Qx when model choice, parameter basis, baseline or challenger design, validation, or citation handoff needs scholarly support. Do not use for generic literature reviews, contest-paper mining, or project result generation."
---

# Literature-Guided Modeling

Turn verified academic papers into question-scoped model choices and testable experiment ideas. Consume the current assembled `literature` prompt packet; do not load or restate the full prompt policy. The packet owns stage behavior, budgets, transition semantics, and stopping conditions.

## Boundaries

- Require the packet's explicit project and Qx. Read only its authorized project-local inputs and write only the canonical literature artifacts for that Qx.
- Own search plans, receipts, Academic Reference Cards, and the Model Evidence Brief. Never own contest state, human decisions, quality contracts, experiment results, frozen claims, Figure Contracts, manuscript sources, or release artifacts.
- Use `nature-academic-search` for discovery, metadata verification, deduplication, and BibTeX work; use the PDF skill for page-aware full-text evidence; use `math-modeling-solver` to turn findings into proposed Scratch probes.
- Accept journal articles, conference papers, preprints, and theses. Prior contest papers cannot support model selection in this skill.
- `references/competition-knowledge/` is a separate, read-only textbook quick-reference layer. Do not load it automatically. When the current packet supplies a relevant card, it may suggest search terms, assumption checks, or risk probes only; it never becomes an Academic Reference Card, BibTeX entry, Formal evidence, claim, or paper citation.
- Keep source PDFs, HTML snapshots, and search caches outside Git, submission, and release directories.
- Never copy an external performance number into a project claim. Project numbers come only from frozen Formal evidence or eligible Paper Evidence.

## Routing

1. **Establish the literature need.** Read `question.yaml` and the literature packet. When authorized, read the question's referenced semantic, metric, and algorithm-evidence contracts only to identify unresolved verification needs; never edit those contracts.
2. **Plan, search, screen, or read.** Before any of these actions, read [search-and-reading.md](references/search-and-reading.md). Use the question interface and named V7.2 gaps to form bounded queries, then create canonical search receipts and depth-labelled cards.
3. **Respond to experiments.** Add a focused query only for a concrete Qx gap exposed by Scratch or Candidate evidence. Keep modeling work independent of literature completion.
4. **Synthesize or hand off citations.** Before either action, read [evidence-contract.md](references/evidence-contract.md). Build a Model Evidence Brief that distinguishes paper evidence from current-problem fit and proposes experiments rather than results.

## V7.2 Verification Inputs

Treat the following as read-only search inputs when present:

- uncovered requirement mappings between the problem statement, model element, required output, primary metric, validation method, and paper location;
- missing known-answer, hand-calculated, exhaustive, exact-solver, analytical-limit, or benchmark cases;
- the need for a same-output baseline, a lightweight challenger, or a reviewed reason that a challenger is not useful;
- unresolved feasibility, conservation, boundary, dimensional, nonnegativity, monotonicity, or interface invariants;
- missing task-specific validation, including prediction leakage and out-of-sample design, optimization bounds or gaps, mechanistic calibration and limits, or ranking stability.

Translate these gaps into literature queries, located evidence, and proposed Scratch checks. Do not mark a contract check as passed, populate an evidence locator, or decide that project evidence is sufficient.

## Outputs

- Search plan and provider receipts with stable identifiers, raw-result hashes, and recorded metadata conflicts.
- Academic Reference Cards with honest depth labels and page, section, equation, table, figure, appendix, or repository locators.
- Model Evidence Brief covering matched and mismatched conditions, implementation cost, parameter basis, comparable baseline, lightweight challenger or omission rationale, risk probes, task-specific validation, rejection triggers, one provisional primary recommendation, and at most one conditional fallback.
- Citation handoff that maps substantive statements to verified cards and BibTeX keys without creating a separate CUMCM literature-review chapter.

The recommendation remains provisional until the project's own experiments support it. A literature contradiction becomes a review suggestion, not a project result or an automatic model change.

## Artifact Integrity

Use the schemas under `config/schemas/` and the corresponding `templates/workflow/literature_*.yaml` templates. Workflow commands derive canonical paths, hashes, timestamps, and lifecycle status; action configuration supplies semantic content only. Do not trust caller-supplied provenance, use absolute paths, create another state file, or invent untracked result numbers.

Compute `source_question_manifest_sha256` from the canonical question interface fields only: `schema_version`, `problem_id`, `question_id`, `source_problem`, and `problem`. Exclude downstream model selection, experiments, paper handoffs, status, and the top-level `literature` block. Drift invalidates only the affected Qx literature artifacts; the current packet determines the appropriate response.
