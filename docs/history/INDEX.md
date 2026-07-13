# Historical Document Index

Status: supporting
Authority: none
Default-read: no
Applies-to: historical document discovery and provenance only
Does-not-authorize: current-state claims, roadmap selection, implementation,
live calls, or protected-surface changes

## Purpose

Current repository truth lives in the current-state owner, the current roadmap
owner, the coding-agent guidance map, and the exact concern-specific
architecture owners. Documents under `docs/history/` preserve provenance only.

Historical wording such as "next phase," "current," or "closed" applies to
the document's original phase unless a current owner explicitly reopens it.
Historical files must not override code, tests, or current canonical docs.

Route here only when a current owner or phase explicitly requires provenance.
Do not treat this index as installed-state, roadmap, or implementation
authority.

Read current owners first:

- [Coding Agent Guidance Map](../codex/CODEX_GUIDANCE_MAP.md)
- [ScryRaven Current State](../architecture/SCRYRAVEN_CURRENT_STATE.md)
- [Current Roadmap](../roadmap/CURRENT_ROADMAP.md)

## Category Indexes

| Category | Index | Count |
| --- | --- | --- |
| Historical architecture phase records (D3B) | [architecture/INDEX.md](architecture/INDEX.md) | 185 |
| Historical validation evidence (D3B) | [validation/INDEX.md](validation/INDEX.md) | 81 |

Archive metadata: [ARCHIVE_MANIFEST.json](ARCHIVE_MANIFEST.json)

## Batch Counts

| Batch | Category | Files |
| --- | --- | ---: |
| D3A | roadmaps | 2 |
| D3A | handoffs | 2 |
| D3A | drafts | 1 |
| D3A | project-source-candidates | 3 |
| D3B | architecture | 185 |
| D3B | validation | 81 |

## D3A Moved Files

| Historical file | Original path | Historical category | Current owner or route |
| --- | --- | --- | --- |
| [roadmaps/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md](roadmaps/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md) | `docs/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md` | roadmap | [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) |
| [roadmaps/ROADMAP_IMPLEMENTATION_NOTES.md](roadmaps/ROADMAP_IMPLEMENTATION_NOTES.md) | `docs/ROADMAP_IMPLEMENTATION_NOTES.md` | roadmap | [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) |
| [handoffs/phase14_checkpoint_handoff_6f7cc76.md](handoffs/phase14_checkpoint_handoff_6f7cc76.md) | `docs/phase14_checkpoint_handoff_6f7cc76.md` | handoff | Guidance map last-resort provenance only |
| [handoffs/phase15_checkpoint_handoff_5e72fcc.md](handoffs/phase15_checkpoint_handoff_5e72fcc.md) | `docs/phase15_checkpoint_handoff_5e72fcc.md` | handoff | Guidance map last-resort provenance only |
| [drafts/source_refresh_phase14_draft.md](drafts/source_refresh_phase14_draft.md) | `docs/source_refresh_phase14_draft.md` | draft | Guidance map last-resort provenance only |
| [project-source-candidates/02_SCRYRAVEN_CURRENT_ARCHITECTURE_AND_RUNAUTHORITY_STATE_v4.md](project-source-candidates/02_SCRYRAVEN_CURRENT_ARCHITECTURE_AND_RUNAUTHORITY_STATE_v4.md) | `outputs/local_only/ag94c_project_source_candidates/02_SCRYRAVEN_CURRENT_ARCHITECTURE_AND_RUNAUTHORITY_STATE_v4.md` | project-source-candidate | Guidance map; Project Sources remain external |
| [project-source-candidates/03_SCRYRAVEN_SOURCE_HIERARCHY_RUNAUTHORITY_AND_EVIDENCE_POSTURE_v4.md](project-source-candidates/03_SCRYRAVEN_SOURCE_HIERARCHY_RUNAUTHORITY_AND_EVIDENCE_POSTURE_v4.md) | `outputs/local_only/ag94c_project_source_candidates/03_SCRYRAVEN_SOURCE_HIERARCHY_RUNAUTHORITY_AND_EVIDENCE_POSTURE_v4.md` | project-source-candidate | Guidance map; Project Sources remain external |
| [project-source-candidates/05_SCRYRAVEN_PRODUCTIZATION_ROADMAP_v11_AUTHORITY_DOCTRINE_AND_OFFICIAL_ACQUISITION.md](project-source-candidates/05_SCRYRAVEN_PRODUCTIZATION_ROADMAP_v11_AUTHORITY_DOCTRINE_AND_OFFICIAL_ACQUISITION.md) | `outputs/local_only/ag94c_project_source_candidates/05_SCRYRAVEN_PRODUCTIZATION_ROADMAP_v11_AUTHORITY_DOCTRINE_AND_OFFICIAL_ACQUISITION.md` | project-source-candidate | Guidance map / [Current Roadmap](../roadmap/CURRENT_ROADMAP.md); Project Sources remain external |
