# Search and Reading Rules

## Search construction

Build two query families from the question interface:

1. Scenario-task: domain object + required output + uncertainty or evaluation condition.
2. Method-constraint: model family or mathematical task + dominant constraint + data condition.

Add a follow-up query only after an experiment exposes a named gap. Stop when the time budget is exhausted even if the literature set is incomplete.

## Source order

Use CrossRef, OpenAlex, and arXiv for discovery and stable identifiers. Use Semantic Scholar for complementary discovery. Treat Google Scholar, CNKI, and Wanfang as manual supplements whose metadata must be verified against a publisher, DOI registry, repository, or another authoritative record.

Accept only journal articles, conference papers, preprints, and theses. Exclude contest papers, blogs, marketing pages, generated summaries, and unsourced method lists from model evidence.

## Deduplication

1. Normalize DOI strings and merge exact DOI matches.
2. When DOI is absent, normalize title punctuation and whitespace, then compare title + first author + year.
3. Preserve all provider identifiers in the search receipt while selecting one canonical record.
4. Record conflicts instead of silently choosing between incompatible author, year, title, or venue fields.

## Screening

Retain no more than 10 candidates. Rank in this order:

1. Same task and output class.
2. Similar hard constraints and data conditions.
3. Implementable within contest time.
4. Comparable baseline and validation design.
5. Available formulas, algorithm details, or code.
6. Source quality and recency.

Do not select a paper only because it reports the best metric. A high score under a different data split, output, or constraint is not evidence of fit.

## Targeted reading

Read the smallest section that can support the pending decision:

- Model family: abstract, end of introduction, related work, and method overview.
- Formula or algorithm: method section, equations, pseudocode, and appendix.
- Parameter: experimental setup and parameter analysis.
- Baseline or metric: evaluation protocol and result-table definitions.
- Limitation: discussion, conclusion, ablation, and failure cases.
- Code: repository metadata, pinned commit, license, inputs, outputs, and reproduction notes.

Use `TARGETED_READ` only after inspecting full text and recording at least one precise locator. Use `DEEP_READ` when the model formulation, experimental protocol, and limitations have all been checked. Abstract-only knowledge never supports an exact formula, parameter, algorithm step, or performance statement.
