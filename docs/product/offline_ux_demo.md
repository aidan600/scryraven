# Legacy Offline UX Demo / Fixture Mode

Status: retired

This document records a fixture-backed mode from the retired legacy Streamlit
shell. It is retained for reference and migration analysis only; it is not
current product usage guidance. The `app.py` compatibility tombstone does not
launch the demo, and no replacement UI framework has been selected.

## Retained legacy material

The historical fixture catalog remains at
[`demo/fixtures/offline_ux_scenarios.json`](../../demo/fixtures/offline_ux_scenarios.json).
The retired shell used it to illustrate:

- ordinary success with source cards and citation markers;
- insufficient or weak evidence;
- source conflict;
- direct-versus-inferred claim labeling;
- a document-review preview mockup;
- error or no-result recovery; and
- Fast, Balanced, and Deep mode labels.

The retained fixtures and Streamlit-specific code are legacy prototype material.
They must not be represented as current product behavior, retrieval validation,
or a selected direction for future UI architecture.

## Boundary

These fixtures never established live product correctness. They must not call or
be used to claim execution of `run_pipeline`, providers, model APIs, search
adapters, retrieval, caches, database rows, raw prompts, raw provider payloads,
or live validation. Their URLs and citations are demonstration metadata only.

Future UI work must consume transport-neutral application services rather than
reactivating or extending this legacy shell.
