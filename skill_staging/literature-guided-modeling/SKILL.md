---
name: literature-guided-modeling
description: "Plan, screen, verify, read, and synthesize academic literature for mathematical-modeling algorithm and model exploration. Use when a contest subproblem needs literature-grounded model candidates, parameter ranges, comparable baselines, validation methods, targeted paper extraction, a model evidence matrix, experiment feedback, or citation handoff without delaying Scratch and baseline work."
---

# Literature-Guided Modeling

Turn academic papers into bounded modeling decisions and testable experiment ideas. Own the search plan, reference cards, and model evidence brief; never own contest state, frozen claims, formal experiment results, or final paper approval.

## Boundaries

- Use `mathmodel-skill` as the only owner of P0-P6, G0-G6, official rules, human decisions, and `state/decision_log.json`.
- Invoke `nature-academic-search` for multi-source discovery, metadata verification, deduplication, and BibTeX work. Follow its router and loaded workflow fragments instead of recreating provider logic.
- Use `math-modeling-solver` to map extracted evidence to candidate models, comparable baselines, parameter probes, and executable Scratch work.
- Use the PDF skill to inspect a supplied full-text PDF, preserve page-aware locators, and distinguish text extraction from visual evidence.
- Use `math-modeling-paper` and `modeling-paper-studio` only for manuscript integration and G5 citation/evidence audits.
- Accept journal articles, conference papers, preprints, and theses. Do not use prior contest papers to choose the model.
- Keep paper PDFs, HTML snapshots, and search caches outside Git, submission packages, and release directories.
- Never copy an external performance number into project claims. Project numbers must come from frozen Formal or eligible Paper Evidence.

## Workflow

1. **Read the question interface.** Require an explicit project and Qx. Read the current `question.yaml`; extract the domain object, mathematical task, inputs, outputs, data conditions, and dominant constraints. Do not create a second workflow state.
2. **Plan a bounded search.** Create `literature/search_plan.yaml` from the canonical template. Include one scenario-task query and one method-constraint query, source priority, a 20-minute per-question limit, a 90-minute project limit, and explicit stopping rules.
3. **Search in parallel with modeling.** Let baseline and Scratch work continue. Search CrossRef, OpenAlex, and arXiv first; use Semantic Scholar next; use Google Scholar, CNKI, and Wanfang as manual supplements. Save a receipt and raw-result hash for every query.
4. **Deduplicate and screen.** Prefer DOI identity; otherwise match normalized title, first author, and year. Screen title and abstract, retain at most 10 candidates, and rank task/output fit before venue prestige or recency.
5. **Read only what the decision needs.** Target 2-4 papers and expand to at most 6 when central evidence is missing. Extract formula, algorithm, parameter, baseline, validation, limitation, and code details only from page- or section-located full text. Read [search-and-reading.md](references/search-and-reading.md) for source and reading rules.
6. **Create evidence cards.** Write one `academic_reference_card` per retained paper. Mark the depth honestly. `METADATA_ONLY` and `ABSTRACT_SCREENED` cards discover candidates only; they cannot support exact formulas, parameters, algorithm steps, or performance claims.
7. **Synthesize model evidence.** Compare candidate families in `model_evidence_brief.yaml`. Record matched and mismatched conditions, implementation cost, baseline, risk probes, rejection triggers, one primary recommendation, and at most one conditional fallback. The recommendation remains provisional until project experiments support it.
8. **Feed experiments back into search.** Add a focused follow-up query only when Scratch exposes a concrete gap such as non-convergence, unsupported parameter bounds, an unfair baseline, an unresolved constraint, or missing robustness evidence. Update only the affected Qx.
9. **Hand off citations.** Map verified BibTeX keys to problem analysis, model selection, parameter basis, or model validation. Do not create a separate literature-review chapter for CUMCM. Read [evidence-contract.md](references/evidence-contract.md) before synthesis or G5 handoff.

## Lifecycle and Gates

Use the project workflow commands when available:

```text
literature-plan -> literature-search -> literature-register
-> literature-read -> literature-synthesize -> literature-audit
```

Derive status from artifacts:

```text
PLAN_READY -> DISCOVERED -> SOURCES_VERIFIED
-> CARDS_READY -> SYNTHESIS_READY -> CITATION_READY
```

Compute `source_question_manifest_sha256` from the canonical P1 problem interface only: `schema_version`, `problem_id`, `question_id`, `source_problem`, and `problem`. Exclude downstream model selection, experiments, paper handoffs, status, and the top-level `literature` block. This avoids a self-referential hash cycle and prevents ordinary downstream progress from invalidating the original search question.

Any question-interface, metadata snapshot, source document, card, or brief hash drift makes only the affected Qx literature chain `STALE`. Literature incompleteness is a warning through G4 and must not block baseline, Scratch, Candidate, or Formal work. G5 requires verified metadata, targeted-read support for substantive citations, current card and brief hashes, referenced BibTeX keys, explained conflicts, and separation between external results and project evidence.

## Canonical Contracts

Use the schema files under `config/schemas/` and start from the corresponding `templates/workflow/literature_*.yaml` files. Treat an action `-Config` file as semantic template payload only; let the workflow command derive the fixed project path, current hashes, timestamps, and lifecycle status. Do not trust caller-supplied provenance fields, invent aliases, use absolute paths, create duplicate status files, or introduce untracked result numbers.
