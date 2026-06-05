# AG-82B Cache Instrumentation and Readiness

Status: instrumentation/readiness only; observer-only; no runtime cache reuse; no live validation; no provider/model/search calls

## Scope

AG-82B adds local-first cache and cost-readiness observations for ScryRaven surfaces that now have stable local IDs and manifests:

- DocumentReviewContext parsing candidates.
- DocumentReviewContext chunk/anchor candidates.
- ProjectSource and SourceRevision manifest candidates.
- Thread report generation candidates.
- Saved report artifact storage candidates.
- Future ProjectSource indexing/retrieval candidates, as observation-only placeholders.

The implementation is deliberately a pure helper surface. Runtime code does not consume readiness records, and readiness records are not cache entries.

## Boundary

AG-82B does **not** implement:

- cache hits;
- memoization;
- runtime cache reuse;
- provider/search result reuse;
- retrieval behavior changes;
- model/provider selection changes;
- prompt behavior changes;
- answer/report reuse;
- Project Source retrieval injection;
- connector behavior;
- database/session/RunOutcome shape changes;
- pipeline/orchestrator hooks.

AG-82C is the future phase that may consider bounded reuse after the candidate keys, privacy scopes, invalidation reasons, and block reasons have been reviewed.

## Record posture

Readiness records are compact, redacted, local/private observations. They include:

- schema version and generator marker;
- observer-only runtime posture;
- candidate surface and digest;
- candidate key fields such as IDs, document hashes, parser metadata, packet/provenance digests, privacy scope, and schema versions;
- invalidation reason labels;
- blocked reuse reason labels;
- coarse cost/latency class labels.

Records must not include raw private document text, raw prompts, full model prompts, raw provider payloads, full traces, report bodies, secrets, database rows, or cache contents.

## Candidate keys

AG-82B candidate keys are for future consideration only. They identify what a later phase would need to compare before any reuse could be safe:

- document hash, input format, parser name/version/confidence, and document-review schema for parse/chunk candidates;
- source record ID, source revision ID, ProjectSource ID, document hash, parser metadata, privacy class, and manifest schema for ProjectSource candidates;
- project ID, report type, report generator, model identity placeholder, packet schema version, packet digest, provenance digest, and privacy scope for report generation candidates;
- source revision, document hash, parser metadata, indexer version placeholder, retrieval profile placeholder, and privacy scope for future ProjectSource indexing/retrieval observations.

## Invalidation and blocked reuse

Invalidation labels cover document hash changes, parser version changes, source revision changes, privacy scope changes, and report packet/provenance digest changes.

Blocked reuse labels include:

- `reuse-disabled-ag82b`;
- `private-scope-not-licensed-for-reuse`;
- `missing-stable-key`;
- `freshness-or-validation-required`;
- `raw-private-text-not-cacheable`.

Every AG-82B record remains blocked from runtime reuse. The records only help AG-82C decide whether a narrower future reuse design is worth proposing.
