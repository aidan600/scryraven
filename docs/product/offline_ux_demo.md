# Offline UX Demo / Fixture Mode (AG-81A)

ScryRaven includes an offline Streamlit demo mode for product-shell and UX review.
It is fixture-backed and does **not** validate retrieval quality.

## Run it

```powershell
streamlit run app.py
```

No API keys are required to view demo fixtures. In the app sidebar, open
**OFFLINE UX DEMO**, choose a scenario, and click **Open offline demo**.

Demo sessions are clearly labeled **OFFLINE DEMO / FIXTURE MODE**. They are not
saved to history, follow-up chat is disabled, and the fixture evidence panel is
labeled separately from live retrieved evidence.

## What it demonstrates

The fixture catalog lives at
[`demo/fixtures/offline_ux_scenarios.json`](../../demo/fixtures/offline_ux_scenarios.json).
It includes canned examples for:

- ordinary success with source cards and citation markers;
- insufficient/weak evidence;
- source conflict;
- direct-vs-inferred claim labeling;
- document-review preview mockup only;
- error/no-result recovery;
- Fast/Balanced/Deep mode-label illustration.

## Boundary

Offline demo mode must not call `run_pipeline`, providers, model APIs, search
adapters, retrieval, caches, DB rows, raw prompts, raw provider payloads, or live
validation. The fixture URLs and citations are demonstration metadata only and
must not be represented as proof of live ScryRaven retrieval behavior.
