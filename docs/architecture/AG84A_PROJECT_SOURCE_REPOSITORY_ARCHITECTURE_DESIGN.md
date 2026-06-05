# AG-84A Project / Source Repository Architecture Design

Status: product architecture / storage architecture design; docs-first; no runtime behavior change; no prompt changes; no provider/model/search calls; no live validation; no storage, project UI, source repository, connector, cache, project-instructions, saved-report, or thread-report implementation

## 1. Purpose and scope

AG-84A turns the AG-84A-R0 product decision record into an implementable architecture design for ScryRaven's Project Sources, Source Repository, saved report/review, and future source-scope seams. AG-84A-R0 locked the vocabulary; this document constrains the object model, storage boundaries, lifecycle states, promotion rules, deletion/retention posture, retrieval scope defaults, and future seams so implementation phases do not invent schema or lifecycle rules ad hoc.

This phase is design-only. It does not implement storage, UI, connectors, cache, project instructions, thread reports, saved reports, prompts, provider/model/search calls, retrieval behavior, source repository code, source picking, database/session/RunOutcome changes, or runtime behavior.

AG-84A prepares **AG-84B — Minimal Project Sources / Saved Source Records Implementation**. It should be read as a set of constraints for later storage/schema/UI phases, not as authorization to implement any closed surface in AG-84A. If a future implementation needs `core/pipeline_orchestrator.py` hooks, AG-84A records the seam only; the orchestrator remains closed and should be strangled by narrow adapters rather than rewritten.

## 2. Current product model recap

AG-84A-R0 locked this product model:

- **Thread**: a conversation plus thread-local attachments and persistent follow-up context inside that same thread.
- **Thread Attachment**: a user-provided file/text/document attached to one thread. It remains thread-local unless explicitly promoted or saved.
- **Project**: the durable user-facing research workspace. It contains Project Sources, future Project Instructions, threads, saved reports/reviews, and scoped connectors.
- **Project Source**: a durable source made available to one Project and eligible for future project context once explicitly attached/promoted.
- **Project Instructions**: a future project-level guidance feature. It is not storage-only metadata if it affects answers and must remain deferred until an explicitly licensed phase opens prompt/Author/Controller/retrieval questions.
- **Source Repository**: backing inventory for durable saved sources, dedupe, versioning, source manifests, and source picking. It is infrastructure, not the main user destination.
- **Connector**: an external access path scoped to a thread or project. Connector access does not imply storage or Source Repository ingestion.
- **Saved Report / Review**: a generated Project artifact that cites back to thread attachments, Project Sources, web evidence, and document anchors. It is not primary evidence by default.
- **Snapshot**: a later explicit capture feature for freezing a state, source set, source content, or report package.

The core model is therefore:

- Project is the durable workspace.
- Source Repository is backing infrastructure.
- Thread Attachments remain thread-local unless promoted.
- Saved reports/reviews live in Projects and cite back to sources.
- Connectors are access paths; access does not imply storage.

## 3. Architecture goals

After AG-84A, AG-84B should be able to implement the smallest safe Project Sources / Saved Source Records slice by following these goals:

- create local Project records;
- save Project Source records;
- promote Thread Attachments or `DocumentReviewContext`-derived sources to Project Sources;
- optionally save durable Source Repository records when the minimal storage path supports it;
- preserve source identity, source revisions, parser metadata, evidence labels, source-obligation classifications, validation posture, and privacy boundaries;
- avoid whole-repository retrieval by default;
- keep generated reports/reviews separate from primary evidence;
- provide a local-first persistence path with a clear schema-version and migration story;
- leave provider/search/retrieval/model/prompt behavior untouched until explicitly licensed.

## 4. Object model

The object model is intentionally small enough for AG-84B, but names future seams so later phases can extend rather than replace it.

### Project

A **Project** is the durable workspace and the primary user-facing container.

Suggested fields:

- `project_id`: stable local ID, such as `proj_<ulid>` or `proj_<uuid>`.
- `name`: user-visible Project name.
- `description`: optional user-visible summary.
- `created_at`, `updated_at`, `archived_at`: UTC timestamps.
- `schema_version`: manifest/storage schema version.
- `privacy_class`: local-private by default; future classes may include workspace-private or shared.
- `project_source_ids`: ordered references to active ProjectSource records.
- `thread_ids`: optional references to threads associated with the Project, if a later phase stores thread membership.
- `saved_report_ids`: references to saved reports/reviews.
- `instruction_ids`: future-only references to ProjectInstruction records.
- `connector_scope_ids`: future-only references to ConnectorScope records.
- `retention_state`: active, archived, deleted, or tombstoned.

AG-84B should start with local Project records and source membership. It should not require a global account model or hosted workspace model.

### ProjectSource

A **ProjectSource** is the Project-scoped membership edge that makes a saved source eligible as Project context.

Suggested fields:

- `project_source_id`: stable local ID for the membership edge.
- `project_id`: owning Project.
- `source_record_id`: optional SourceRecord reference if the source is saved in the Source Repository.
- `source_revision_id`: the revision/manifestation attached to the Project.
- `title`: Project-local display title; may differ from SourceRecord title.
- `source_kind`: document, pasted_text, markdown, pdf, docx, web_url, web_snapshot, connector_result, note, or future explicit kinds.
- `scope`: project-source.
- `privacy_class`: local-private by default for uploaded/promoted documents.
- `evidence_role`: primary-evidence, document-local-evidence, supporting-reference, citation-only-reference, generated-artifact, or future explicit values.
- `source_obligation_summary`: derived classification summary where available, such as document-local-only, external-validation-required, official-current-source-needed, or mixed.
- `validation_posture`: not-validated-outside-document, validated-current, stale, citation-only, unresolved, or future explicit values.
- `added_at`, `updated_at`, `removed_at`: UTC timestamps.
- `retention_state`: active, removed-from-project, deleted, tombstoned.
- `provenance`: promotion source, such as ThreadAttachmentRef, DocumentReviewContext metadata, web URL, connector identity, or manual entry.
- `anchor_index_ref`: reference to anchors/chunks in a source manifest when available.
- `display_order`, `tags`: optional local organization metadata.

ProjectSource is not a copy of all source text by itself. It points to a SourceRevision/manifestation or carries a compact inline manifest only in the minimal AG-84B storage path.

### SourceRecord

A **SourceRecord** is the durable backing Source Repository object for a saved source that can be reused across Projects.

Suggested fields:

- `source_record_id`: stable repository ID.
- `canonical_title`: source-level title.
- `source_kind`: document, pasted_text, markdown, pdf, docx, web_url, web_snapshot, connector_result, or future explicit kind.
- `created_at`, `updated_at`, `deleted_at`: UTC timestamps.
- `privacy_class`: local-private, project-private, public-reference, authenticated-private, or future explicit values.
- `owner_scope`: local-user, project, workspace, or future hosted scope.
- `current_revision_id`: selected latest revision.
- `revision_ids`: ordered list of SourceRevision/Manifestation IDs.
- `dedupe_keys`: byte hash, extracted text hash, canonical URL, connector identity, parser identity, and other stable keys.
- `project_memberships`: optional back references or derived index of ProjectSource IDs.
- `retention_state`: active, deleted, tombstoned.
- `provenance`: initial creation source, such as promoted Thread Attachment, manual save, web capture, connector save, or import.

AG-84B may either create SourceRecords immediately or use a Project-local source manifest with fields shaped so SourceRecord can be introduced without migration churn. If storage simplicity wins, SourceRecord can be an optional backing record while ProjectSource stores source identity and revision fields directly.

### SourceRevision / Manifestation

A **SourceRevision** or **Manifestation** represents one version or extracted/rendered form of a SourceRecord.

Suggested fields:

- `source_revision_id`: stable revision ID.
- `source_record_id`: owning SourceRecord.
- `revision_label`: user-visible or generated label, such as `v1`, `2026-06-04-upload`, or `snapshot-<timestamp>`.
- `created_at`: UTC timestamp.
- `source_kind`: repeated for validation and migration clarity.
- `file_name`, `media_type`, `file_size_bytes`: file metadata where applicable.
- `byte_hash`: hash of original bytes when available.
- `extracted_text_hash`: hash of normalized/extracted text when available.
- `document_id`, `document_hash`: values from `DocumentReviewContext` when promoted.
- `parser_name`, `parser_version`, `parser_confidence`, `parser_notes`: parser metadata.
- `chunker_version`, `anchor_schema_version`: later explicit versions if chunks/anchors are persisted.
- `managed_copy_path`: local managed copy path when the user chooses a copy-based storage mode.
- `linked_file_path`: local path reference when the user chooses linked-file storage.
- `normalized_text_path`: optional local-private derived text path; not safe to commit.
- `anchor_manifest_path`: optional path to anchor/chunk manifest.
- `source_url`, `canonical_url`: future web identities.
- `snapshot_timestamp`, `fetched_at`: future web snapshot identities.
- `connector_identity`: future connector source identity, excluding secrets.
- `retention_state`: active, superseded, deleted, tombstoned.

A source can have several manifestations for the same revision, such as original bytes, normalized text, anchor manifest, and future preview image. AG-84B should avoid overbuilding this: one compact revision manifest is sufficient if it preserves the above identity fields.

### ThreadAttachmentRef

A **ThreadAttachmentRef** records provenance from a thread-local attachment without turning every attachment into a Project Source.

Suggested fields:

- `thread_id`: originating thread.
- `attachment_id`: thread-local attachment ID, if available.
- `attachment_name`: display filename/title.
- `attached_at`: UTC timestamp if available.
- `source_kind`: pasted_text, markdown, pdf, docx, file, or future explicit kind.
- `document_review_context_id`: derived `DocumentReviewContext.metadata.document_id` when the attachment was reviewed.
- `document_hash`: `DocumentReviewContext.metadata.document_hash` when available.
- `promotion_status`: not-promoted, promoted-to-project, saved-to-repository, removed, deleted.
- `privacy_class`: session-local-private-document or local-private.

This object is a provenance link, not a retrieval surface.

### SavedReport / ReviewArtifact

A **SavedReport** or **ReviewArtifact** is a generated Project artifact, not primary evidence by default.

Suggested fields:

- `report_id`: stable report ID.
- `project_id`: owning Project.
- `originating_thread_id`: thread that produced the synthesis, if applicable.
- `generated_at`: UTC timestamp.
- `report_type`: thread_report, document_review_export, synthesis_report, note, or future explicit kind.
- `title`: user-visible title.
- `body_path` or `export_path`: local saved Markdown/HTML/text path.
- `cited_source_refs`: SourceRecord/ProjectSource/web evidence references.
- `cited_document_anchors`: document anchor IDs with source revision references.
- `unresolved_gaps`: explicit gaps or validation needs.
- `evidence_posture_labels`: document-local, external-validation-required, official-current-needed, citation-only, mixed, or future explicit values.
- `model_prompt_version_metadata`: future-only and only if a licensed phase adds model-mediated generation metadata.
- `retention_state`: active, archived, deleted, tombstoned.

Saved reports must not launder generated text into primary evidence. If a later retrieval phase uses reports/notes, it must label them as generated artifacts and preserve source links.

### ConnectorScope (future only)

A **ConnectorScope** records that a connector access path is enabled for a thread or Project.

Suggested fields:

- `connector_scope_id`;
- `scope_kind`: thread or project;
- `scope_id`: thread_id or project_id;
- `connector_type`: future explicit value;
- `enabled_at`, `disabled_at`;
- `privacy_class` and `auth_boundary`;
- `retention_policy_ref`;
- `allowed_actions`: read, attach-result-to-thread, save-result-as-source, or future explicit actions.

ConnectorScope does not store connector content and does not imply Source Repository ingestion.

### ProjectInstruction (future only)

A **ProjectInstruction** is future Project-level guidance that can affect answers.

Suggested fields:

- `instruction_id`;
- `project_id`;
- `title`;
- `body`;
- `created_at`, `updated_at`, `disabled_at`;
- `instruction_type`: style, scope, research preference, citation preference, or future explicit values;
- `risk_class`: low, answer-affecting, retrieval-affecting, prompt-affecting;
- `activation_policy`: future Controller/AnswerContract policy reference.

Because Project Instructions can affect prompts, Author behavior, Controller decisions, retrieval, and final-answer posture, they are deferred beyond AG-84A/AG-84B.

### Snapshot (future only)

A **Snapshot** freezes a source set, source revision, web content, Project state, or report package.

Suggested fields:

- `snapshot_id`;
- `snapshot_kind`: source, project_source_set, report_package, web_page, connector_result, or future explicit values;
- `created_at`;
- `source_record_ids` and `source_revision_ids`;
- `content_hashes`;
- `snapshot_timestamp`;
- `retention_state`;
- `export_path`;
- `privacy_class`.

Snapshots are not created by default; they require an explicit capture phase.

### ProjectContext (future aggregate)

A **ProjectContext** is the future assembled context object for a project-scoped thread.

Suggested fields:

- `project_id`;
- `active_project_source_ids`;
- `active_thread_attachment_refs`;
- `instruction_refs` only if a future phase licenses instructions;
- `connector_scope_refs` only if a future phase licenses connectors;
- `retrieval_scope_policy`;
- `privacy_boundary`;
- `source_obligation_digest`;
- `assembled_at`;
- `context_version`.

ProjectContext is a retrieval/model seam. AG-84A and AG-84B should not implement it as runtime context.

### SourceRepositoryManifest

A **SourceRepositoryManifest** is a local manifest for durable saved source inventory.

Suggested fields:

- `manifest_schema_version`;
- `repository_id`;
- `created_at`, `updated_at`;
- `source_records`: map from source_record_id to SourceRecord summaries;
- `source_revisions`: map from source_revision_id to SourceRevision summaries;
- `dedupe_index`: optional hash/key to source_record_id list;
- `tombstones`: deleted source stubs safe for saved-report citations;
- `migration_history`: schema migration markers;
- `storage_roots`: managed copy, derived text, anchors, reports, and manifest paths.

AG-84B should keep this small and human-inspectable if JSON is chosen.

## 5. Source identity and versioning

Source identity must distinguish source-level sameness from revision-level changes.

Identity keys:

- **Byte hash**: hash of original bytes for uploaded files and managed copies. It detects unchanged binary/source bytes.
- **Extracted text hash**: hash of normalized extracted text. Existing `DocumentReviewContext` uses a SHA-256 digest of normalized text as `document_hash` and derives `document_id` from that hash.
- **Parser version**: parser name/version/confidence/notes from document review or a later parser. Parser drift can change anchors or extracted text.
- **Source kind**: pasted text, Markdown, PDF, DOCX, web URL, web snapshot, connector result, generated artifact, etc.
- **Local file path or managed copy path**: path identity is provenance and convenience, not sufficient identity.
- **Document ID/hash from DocumentReviewContext**: durable bridge from AG-83 review output to Project Sources.
- **URL/canonical URL**: future web source identity. URL identity alone is not frozen evidence.
- **Snapshot timestamp**: future frozen web/source state identity.
- **Connector source identity**: future connector-backed identity without secrets, preserving auth/tenant boundaries.

Rules:

- **Renamed files**: if byte hash and extracted text hash match, treat as the same SourceRevision with updated display/provenance metadata, not a new source.
- **Moved files**: a linked-file path change should update path metadata. A managed copy should be unaffected. Path alone must not force a new source.
- **Duplicate files**: identical byte hash and source kind should dedupe to the same SourceRecord candidate. ProjectSource can link the same SourceRecord into multiple Projects.
- **Same file in multiple Projects**: use one SourceRecord with multiple ProjectSource memberships when privacy scope permits. If privacy scopes differ, create separate SourceRecords or block cross-project reuse.
- **Changed file bytes**: create a new SourceRevision under the same SourceRecord if provenance/user intent says it is the same source updated over time; create a new SourceRecord if the source identity or user intent is different.
- **Same extracted text with different file bytes**: same normalized text may indicate equivalent content with different formatting. Keep a distinct SourceRevision/manifestation if byte hash differs, but dedupe can suggest linking to the same SourceRecord.
- **Same URL fetched at different times**: each fetch is a new snapshot/revision if content is captured. A URL bookmark without fetched content is a citation-only or pointer record, not durable source content.
- **Parser/version drift**: if parser version, extraction confidence, extracted text, anchors, or chunking changes, create a new SourceRevision or reindex manifestation. Do not silently reuse stale anchors.
- **New revision vs new source**: new revision when user intent/provenance/canonical identity is continuous; new source when canonical URL, connector identity, document lineage, source kind, or privacy scope changes materially.

## 6. Storage model options

AG-84A does not implement storage. It defines options and recommends the minimal AG-84B shape.

Options:

1. **JSON manifest files**
   - Pros: human-inspectable, local-first, simple tests, easy migration markers, low implementation cost.
   - Cons: concurrency and large indexes are weaker than SQLite; careful path hygiene is required.
2. **SQLite tables**
   - Pros: queryable, dedupe indexes, transactional writes, scalable for source pickers.
   - Cons: less inspectable, requires schema migrations, risks touching DB/session/RunOutcome surfaces if not isolated.
3. **Project folders**
   - Pros: natural local workspace shape; easy export/backup; clear per-Project boundaries.
   - Cons: dedupe across Projects needs a repository manifest or index.
4. **Managed copy directory**
   - Pros: stable bytes, safe against linked-file moves, supports byte hashing and deletion.
   - Cons: stores private documents locally; requires explicit retention and privacy rules.
5. **Linked-file references**
   - Pros: avoids copying private documents; lower storage usage.
   - Cons: broken links, path privacy leakage, moved files, and weak revision control.
6. **Hybrid manifest + file store**
   - Pros: small JSON manifests plus managed copies/derived manifests; easiest migration to SQLite later.
   - Cons: more paths to validate and delete.

Recommended minimal AG-84B storage shape:

- Use **local JSON manifests** with explicit `schema_version` for Projects and ProjectSources.
- Use a **project folder** or local application data folder for project manifests; do not commit raw private documents to the repo.
- Support either a minimal **managed copy directory** or explicit **linked-file reference** policy, but choose one in AG-84B based on implementation scope and privacy UX. If unresolved, AG-84B should stop rather than mix both silently.
- Store compact SourceRevision identity and parser metadata in the manifest.
- Store anchors/chunks as a compact source manifest only when promoted from `DocumentReviewContext`; keep raw normalized text local-private and out of logs/traces.
- Keep Source Repository manifest optional for the first slice if ProjectSource records already include source identity and revision fields shaped for later promotion.

Storage requirements:

- No raw private documents committed to the repository.
- Local-only by default.
- Deletion and retention states must be representable before broad source saving ships.
- Every manifest must include schema/migration version.
- Human-inspectability is preferred for the first local implementation.
- Raw trace/log/cache leakage must be avoided; project/source storage must not copy raw provider payloads, raw prompts, full traces, DB rows, private logs, or caches.
- Storage differs from cache: source records are user-authorized durable sources; cache artifacts are optimization candidates and never evidence by default.
- Source records differ from saved reports: source records preserve evidence identity/content/provenance; reports are generated artifacts that cite evidence.

## 7. Thread Attachment -> Project Source promotion

Promotion is explicit and preserves boundaries:

1. **Thread-local attachment**: a file/text/document is attached to a thread and is persistent only in that thread.
2. **Reviewed document context**: document review builds a `DocumentReviewContext` with normalized text, metadata, anchors, chunks, findings, parser metadata, boundary notice, and privacy warning. Existing review is session-local and does not persist a corpus/library.
3. **Promote to Project Source**: user explicitly adds the attachment/reviewed document to one Project. AG-84B records ProjectSource membership and source identity.
4. **Optionally save SourceRecord**: if repository storage is included, create or reuse a SourceRecord and SourceRevision.
5. **Preserve anchors/chunks/parser metadata**: when available, copy compact anchor/chunk manifests and parser metadata so citations remain tied to the promoted revision.
6. **Preserve document-local evidence boundary**: evidence labels such as document-local-evidence, document-local-only, source scope, source obligations, and validation posture must survive promotion.
7. **Avoid promoting generated reviews as primary evidence**: a document review export can be saved as a report/artifact, but the source document remains the primary evidence.

Promotion outcomes:

- attach only to thread;
- promote to one Project;
- save reusable SourceRecord;
- link the same SourceRecord into multiple Projects when privacy allows;
- remove from Project without deleting SourceRecord;
- delete/tombstone a source in a later retention phase.

## 8. Project Sources and retrieval scope

Active Project context is the explicitly selected ProjectSource set plus any future explicitly scoped Project Instructions or connector scopes. AG-84A and AG-84B do not implement retrieval behavior.

Guidance:

- Project Sources are eligible project context once explicitly attached/promoted.
- Thread Attachments remain thread-local and must not become Project context unless promoted.
- Source Repository records are inactive unless selected for a Project or explicitly scoped by a future source picker.
- Whole Source Repository retrieval is explicit, not default.
- Generated Saved Reports are not primary evidence unless a later phase defines report/note retrieval with generated-artifact labels.
- Future Controller/model seams should receive Project Sources as a bounded, reviewable, Project-scoped source set, not a global repository dump.
- Future retrieval should preserve ProjectSource IDs, SourceRevision IDs, source obligations, parser metadata, anchor references, privacy class, and validation posture.

## 9. Source Repository role

The Source Repository is backing inventory, not the main workspace.

Its roles:

- durable saved source inventory;
- source picker backing store;
- dedupe and versioning;
- reusable SourceRecords;
- source revision/manifestation management;
- tombstone and provenance index;
- optional future indexing substrate.

It is not:

- the main user-facing Project workspace;
- injected into answers by default;
- a whole-account “search everything” surface;
- a junk drawer for generated outputs;
- a cache, raw trace store, provider payload archive, or prompt archive.

Belongs in Source Repository:

- user-saved durable sources;
- promoted documents;
- future web snapshots;
- future connector-backed saved sources created by explicit action.

Does not belong by default:

- every thread attachment;
- every connector result;
- every generated report;
- raw logs, traces, caches, raw prompts, raw provider payloads;
- unreviewed provider payloads.

## 10. Saved Reports / Reviews architecture

A saved report/review is a generated Project artifact. It may preserve useful synthesis, but it must cite back to primary evidence and carry provenance.

Future fields for AG-86A:

- `report_id`;
- `project_id`;
- `originating_thread_id`;
- `generated_at`;
- `report_type`;
- `title`;
- `body_path` or `export_path`;
- `cited_source_refs`;
- `cited_document_anchors`;
- `unresolved_gaps`;
- `evidence_posture_labels`;
- `model_prompt_version_metadata` only if a future licensed phase adds model-mediated generation.

Anti-laundering rules:

- Generated reports are not primary evidence by default.
- A report citation to a ProjectSource does not copy the ProjectSource into the report as independent evidence.
- If a cited source is deleted, the report can retain a safe tombstone citation stub but not private source text unless retention explicitly allows it.
- If future retrieval uses saved reports/notes, generated-artifact labels must remain visible to Controller/AnswerContract and citation presentation seams.
- Document review exports can be saved as artifacts, but the document/revision/anchors are the evidence.

## 11. Project Instructions future seam

Project Instructions are future project-level guidance. Likely fields include instruction ID, Project ID, title, body, enabled/disabled state, timestamps, instruction type, risk class, and activation policy.

Risk surfaces:

- prompt assembly;
- Author prose/final-answer posture;
- Controller planning and AnswerContract behavior;
- retrieval scope and source prioritization;
- citation preferences;
- safety/privacy rules.

Rules:

- Project Instructions are not storage-only metadata if they affect answers.
- They may open protected prompt, Author, Controller, AnswerContract, or retrieval behavior.
- They need their own phase brief and explicit license.
- No Project Instructions implementation is authorized in AG-84A or AG-84B unless a later phase explicitly opens it.

## 12. Connector scope future seam

Connector states should be separated:

- connector enabled for a thread;
- connector enabled for a Project;
- connector result attached to a thread;
- connector result saved as Project Source only by explicit action;
- authenticated/private connectors deferred.

Rules:

- Connector access is not storage.
- Connector retrieval is not automatic Source Repository ingestion.
- Connector content must preserve privacy, auth, tenancy, and retention boundaries.
- Connector-backed saved sources are future work.
- Secrets, tokens, raw authenticated payloads, and private connector logs must not enter Project/source manifests.

## 13. Web source and snapshot future seam

Future web source states:

- URL record/bookmark;
- fetched readable text, later;
- local snapshot, later;
- archival copy, much later;
- citation-only reference;
- authenticated web deferred.

Rules:

- A URL record is not the same as a fetched snapshot.
- A citation is not the same as local durable source content.
- A live URL is not frozen evidence.
- Snapshots require timestamp, content hash, canonical/source URL metadata, fetch metadata, retention/deletion semantics, and privacy class.
- Current/legal/official source obligations still require freshness policy; a stale snapshot must not satisfy a current-source obligation without explicit validation.

## 14. Privacy, deletion, and retention

ScryRaven's first Project/source storage path should be local-first and private by default.

Rules:

- Deleting a Project link should not necessarily delete the SourceRecord.
- Removing a ProjectSource from a Project should set membership state to removed-from-project or delete only the membership edge.
- Deleting a SourceRecord should delete or invalidate derived chunks, anchors, indexes, normalized text, managed copies, and cache candidates tied to that source.
- Deleting a SourceRecord should leave safe tombstones where saved reports cite it.
- Generated reports may retain citation stubs without retaining private source text.
- Project archival/deletion is future work, but retention states must be representable from the first source-storage implementation.
- Export privacy must distinguish source exports, report exports, tombstone references, and generated summaries.
- Private documents must remain local-private unless a future phase designs sync/hosted/sharing behavior.
- No raw provider payloads, full traces, caches, private logs, raw prompts, secrets, `.env` values, API keys, DB rows, or unrelated generated outputs belong in project/source storage.

## 15. Cache/instrumentation implications

AG-82A separated cache architecture from runtime reuse. AG-84A provides stable source/project object boundaries so future AG-82B instrumentation can observe cacheability without changing behavior.

Implications:

- Document parsing cache can key on byte hash, extracted text hash, parser name/version, source kind, privacy scope, and source revision.
- Chunking/anchor cache can key on extracted text hash, chunker/anchor schema version, parser version, and source revision.
- Project-source indexing can key on ProjectSource ID, SourceRevision ID, source-obligation digest, privacy scope, and index version.
- Source revision invalidation must clear or mark stale derived chunks, anchors, indexes, and cache candidates.
- Cache instrumentation must remain redacted and local/private by default.
- Cache artifacts are not SourceRecords.
- Cache hits must not launder stale or private context into answers.
- AG-82B may instrument source/project/cacheability only after object boundaries are stable.
- AG-84A authorizes no runtime cache reuse.

## 16. Minimal AG-84B implementation slice

Recommended smallest useful implementation:

- create local Project records;
- add/list Project Sources from an existing `DocumentReviewContext` or uploaded/local document-review output;
- use a simple local manifest with schema version;
- record source ID, revision ID, byte hash when available, extracted text/document hash, source kind, privacy class, project membership, evidence role, source-obligation summary, and validation posture;
- preserve parser metadata when promoted from document review;
- preserve anchor/chunk references or a compact source manifest when available;
- optionally create a minimal SourceRecord/SourceRevision manifest if it does not expand scope;
- keep retrieval integration absent, or expose only an inert source picker/list if safer;
- no Project Instructions;
- no connectors;
- no snapshots;
- no whole-repository search;
- no prompt/model/provider/search behavior changes.

AG-84B stop conditions:

- storage choice is unresolved between incompatible backends;
- implementation requires DB/session/RunOutcome shape changes beyond licensed scope;
- retrieval behavior must change;
- connector behavior is needed;
- Project Instructions are needed;
- source deletion/retention cannot be safely represented;
- broad `core/pipeline_orchestrator.py` work appears necessary;
- private document retention UX cannot be made explicit enough for the chosen storage mode.

## 17. Follow-on roadmap

### AG-84B — Minimal Project Sources / Saved Source Records Implementation

Scope: local Project records, ProjectSource add/list, source identity/revision manifest, document-review promotion, parser metadata preservation, deletion/removal states.

Non-goals: retrieval integration, prompts, provider/model/search calls, connectors, Project Instructions, snapshots, saved report generator, cache reuse, hosted sync.

Likely touched surfaces: new isolated project/source storage module, narrow UI/source list or non-runtime helper, docs/tests for manifest shape. Avoid `core/pipeline_orchestrator.py`.

Stop conditions: unresolved storage backend, required DB/session/RunOutcome changes, retrieval changes, connector need, instruction need, unsafe deletion semantics.

Protected surfaces remain closed unless explicitly licensed: prompts, Controller/AnswerContract runtime, Author/Analyst/Economist/Scrutineer behavior, provider/search/retrieval, cache behavior, broad orchestrator rewrite.

### AG-86A — Thread Report Generator / Save Thread Synthesis to Project

Scope: generated report artifact model, report save action, provenance/citations, unresolved gaps, evidence posture labels, anti-laundering enforcement.

Non-goals: treating reports as primary evidence, changing final answer behavior, adding provider/model calls beyond an explicitly licensed generator flow, whole-repository retrieval.

Likely touched surfaces: saved report artifact storage, export surface, Project report list, provenance renderer.

Stop conditions: report generation requires prompt/Author/Controller changes not licensed, citation provenance cannot be preserved, private source deletion cannot leave safe stubs.

Protected surfaces remain closed unless explicitly licensed: prompt stack, Author final posture, Controller/AnswerContract runtime, retrieval ranking, final citation behavior.

### AG-82B — Cache Instrumentation and Readiness, no reuse yet

Scope: redacted cacheability observations for project/source parsing, chunking, indexing, and source revision invalidation candidates.

Non-goals: runtime cache hits, provider/search reuse, answer/citation reuse, storing raw private source text in cache telemetry.

Likely touched surfaces: redacted telemetry appenders or adjacent instrumentation, docs/tests proving no runtime decisions use cache candidates.

Stop conditions: cache telemetry requires raw prompts/provider payloads/private documents, cache keys are unstable, source identity/revision boundaries are not implemented.

Protected surfaces remain closed unless explicitly licensed: runtime cache behavior, cache keys used for decisions, provider/search/retrieval behavior, DB/session/RunOutcome shape.

### Future Project Instructions

Scope: project-level answer guidance with explicit risk classification and activation policy.

Non-goals: silent prompt mutation, unbounded instruction influence, storage-only implementation that affects answers accidentally.

Likely touched surfaces: prompt assembly, Controller/AnswerContract policy, retrieval scope policy, UI edit/review surface.

Stop conditions: prompt/Author/Controller/retrieval surfaces are not explicitly licensed, instruction conflict rules are unresolved, safety/privacy handling is unclear.

Protected surfaces: all prompt/model/Author/Controller/retrieval behavior until a phase brief opens them.

### Future connector-backed sources

Scope: explicit save of connector result as ProjectSource/SourceRecord with privacy/auth/retention metadata.

Non-goals: automatic ingestion of every connector result, token/secret storage in manifests, treating connector access as durable storage.

Likely touched surfaces: connector result attachment seam, source save action, privacy/auth metadata, deletion/invalidation.

Stop conditions: authenticated connector boundaries are unclear, retention/legal posture is unresolved, source identity cannot avoid secrets.

Protected surfaces: connector implementation, provider/search/retrieval behavior, source repository ingestion automation.

### Future snapshots

Scope: explicit capture of source/web/project/report state with timestamp, content hash, manifest, deletion semantics, and export posture.

Non-goals: implicit snapshots for every URL/access/report, stale snapshot satisfying current obligations automatically, archival/legal claims without design.

Likely touched surfaces: snapshot manifest, source revision storage, export/retention UI.

Stop conditions: legal/privacy retention is unresolved, freshness rules are unresolved, snapshot deletion cannot invalidate derived artifacts.

Protected surfaces: web fetching, authenticated web, retrieval reuse, cache reuse.

### Future source picker/retrieval integration

Scope: explicit ProjectSource and Source Repository source selection, bounded retrieval context assembly, source-obligation-aware indexing.

Non-goals: global search everything by default, changing final evidence/citation ordering without license, injecting repository records into all answers.

Likely touched surfaces: source picker UI, ProjectContext aggregate, retrieval adapter, Controller seam.

Stop conditions: Controller/AnswerContract changes are needed but not licensed, retrieval ranking/filtering must change, citation behavior must change, source privacy boundaries are not enforceable.

Protected surfaces: provider/search/retrieval, Controller/AnswerContract runtime, citation/source ordering, final web evidence selection.

### Future local packaging/security posture

Scope: local path policy, encryption-at-rest choices, export/backup posture, private document retention UX, platform-specific app data directories.

Non-goals: hosted deployment, enterprise tenancy, cloud sync.

Likely touched surfaces: storage root selection, manifest paths, deletion UX, export packaging.

Stop conditions: private document storage policy is unclear, platform-specific path handling is unsafe, export could leak raw private text unintentionally.

Protected surfaces: hosted deployment, sync/share, secrets, raw logs/traces/provider payloads.

## 18. Explicit non-goals

AG-84A keeps these surfaces closed:

- prompts;
- model calls;
- provider/search/retrieval behavior;
- provider routing, depth, selection, swaps, or new providers;
- query generation;
- query finalization;
- recency merge;
- official-bias insertion;
- query ordering;
- retrieval ranking/filtering;
- final web evidence selection;
- citation behavior/source ordering;
- Author prose or final-answer posture;
- Analyst/Economist/Scrutineer/synthesis-evaluator behavior;
- Controller runtime behavior;
- AnswerContract runtime behavior;
- DB/session/RunOutcome runtime shape;
- project/source storage implementation;
- connector implementation;
- cache behavior;
- cache keys;
- runtime cache reuse;
- project instructions implementation;
- thread report generator implementation;
- package/CLI/env compatibility rename;
- live validation;
- hosted deployment;
- broad `core/pipeline_orchestrator.py` rewrite.
