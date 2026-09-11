# Local Evaluation Corpus

This is the durable operating contract for ScryRaven's optional local evaluation
evidence corpus. It preserves useful, sanitized evidence across experiments and
aftercare without publishing actual cases to GitHub or making evaluation data a
product dependency.

## Location and boundary

The corpus lives at:

```text
C:\Users\aidan\ScryRaven\local-evals\
```

Its repository-relative location is `local-evals/`. Git ignores that directory;
`.cursorignore` intentionally does not exclude it. A local coding agent may
inspect it only when an approved work item licenses corpus use. ChatGPT/project
sources do not receive it automatically, and ordinary product runtime must not
depend on it. A fresh clone must work with no `local-evals/` directory.

The corpus is local, not a dumping ground for private execution data. Store only
public or synthetic, sanitized material such as the research question, exact
selected evidence from public sources, public source identities and URLs,
structured Analyst output, an answer, safe configuration metadata, failure
classification, adjudication, semantic obligations, bounded counters, hashes,
and provenance references. Never store credentials, API keys, `.env` contents,
raw private provider payloads, hidden reasoning or chain of thought, secret-bearing
prompts, private user data, unrelated logs, databases, credential-broker
internals, unredacted secret-bearing traces, or caches merely because they exist.
If exact evidence is not safe to preserve, keep only a metadata/provenance record
or do not create the case. Never reconstruct missing exact evidence from memory
and label it exact.

## Layout and case records

The intentionally small local layout is:

```text
local-evals/
  README.md
  index.json
  cases/       # adjudicated cases
  candidates/  # captured but not yet adjudicated cases
  runs/        # experimental outputs, separate from case gold
```

An adjudicated runnable case should be self-contained enough to establish what
was evaluated. A case directory may contain:

```text
case.json
question.txt
selected-evidence.json
analyst.json
answer.md
evaluation.json
safe-trace.json       # optional
presentation.html     # optional
notes.md              # optional
```

`case.json` identifies which artifacts exist; historical cases do not need every
file. A candidate may use the same files under `candidates/` until it is
adjudicated. `index.json` is a small versioned list of case manifests, not a
database.

Each manifest should support at least:

- `schema_version`, `case_id`, `title`, `captured_at`, `origin`, and
  `repo_revision`;
- `question_kind` (`natural` or `synthetic`) and `question_file`;
- `capture_status` (`candidate`, `adjudicated`, or `retired`);
- `use_status` (`reserved` or `development`) and `runnable`;
- `failure_layer`, `outcome_class`, and descriptive `tags`;
- safe model/configuration metadata when known;
- a public-data declaration;
- artifact file references, provenance notes, and hashes for immutable/frozen
  artifacts where practical.

Use these semantic failure layers:

```text
research_selection
analyst_interpretation
author_fidelity
citation_provenance
partial_unable_boundary
product_behavior
unknown
```

Use these outcome classes where applicable:

```text
material_error
minor_error
clean_control
expected_partial
expected_unable
```

Descriptive selection tags may include `quantitative`, `comparison`, `policy`,
`modal`, `epistemic`, `condition`, `exception`, `temporal`, `currentness`,
`multi_source`, `single_source`, `long_context`, `synthetic`, `natural`,
`authority`, and `citation`. Tags help selection; they are not semantic rules.

## Lifecycle and held-out meaning

The intended flow is:

```text
valuable failure/control observed
  -> freeze relevant exact artifacts
  -> sanitize
  -> create local candidate
  -> hash and record provenance
  -> adjudicate when useful
  -> classify failure layer and outcome
  -> assign reserved/development status
  -> future experiment selects case IDs
  -> preserve the result as a separate run record
```

New captures normally start as `capture_status: candidate`. Human or review
evidence can move a case to `adjudicated`; a case can later be `retired` with a
reason. `use_status: reserved` means the intervention being evaluated was not
designed from that case. Once the case or its gold defects informs intervention
design, tuning, repair, or selection, set `use_status: development`. A new Codex
window, branch, model call, or experiment does not restore held-out status.

Adjudicated `evaluation.json` should support:

```json
{
  "severity": "material",
  "known_issues": [
    {"kind": "qualification_loss", "severity": "material", "description": "A required condition was omitted.", "where": "answer"}
  ],
  "obligations": ["Preserve both published values and the stated comparison condition."],
  "prohibited_mutations": ["Present the difference as an unqualified like-for-like change."],
  "permitted_variation": ["Wording and optional arithmetic explanation may vary."],
  "adjudication": {"provenance": "human review of the frozen public evidence", "revised_at": null},
  "limitations": []
}
```

The example is generic/synthetic, not a ScryRaven failure case. Prefer these
semantic obligations and prohibited mutations over one canonical prose answer.
Human-approved or previously frozen labels must not be silently changed to make
a later experiment pass. If review finds the old gold genuinely wrong, record a
revision and its reason while preserving the history.

## Capture and experiment rules

Capture before cleanup when a run contains plausibly reusable evidence: freeze
the exact question, selected evidence, answer, relevant structured outputs, and
safe provenance; sanitize; then hash the frozen artifacts. Public/synthetic exact
evidence is preferred to reconstructed prose. If an aftercare step would remove
the only useful exact copy, follow the standing rule in `AGENTS.md` before
deleting it.

Future experiments should select by manifest metadata such as case ID, failure
layer, outcome class, tags, `reserved`/`development`, question kind, and
`runnable`. A small deterministic sampler may use case IDs plus a random seed;
this corpus does not define a model judge, evaluation service, database, or
runtime framework. Experimental outputs belong in a new `runs/` record that
references case IDs. They must not overwrite the frozen case or its gold.

## Pytest and ordinary PRODUCT evidence

The corpus is evaluation evidence, not an ordinary deterministic unit-test
suite. Pytest and CI may verify tracked schema/tooling or utilities against
synthetic temporary fixtures, but must not require `local-evals/`, private case
contents, live providers, or semantic model judgments. No tracked code or test
may require the corpus to exist. An ordinary PRODUCT observation may motivate a
local case, but a local case cannot replace ordinary PRODUCT evidence for a
product claim.
