# Dynamic Highlights Integration 01

## Decision and provenance

The original Dynamic Highlights Context Allocation 01 experiment was formally
**INCONCLUSIVE** under its preregistered whole-product promotion gate. Its bounded
provider observations showed the intended uneven allocation and preserved source
selection custody, but did not prove downstream answer or cost superiority. The
later human architecture decision selected Dynamic/high as the retrieval mechanism
for ordinary generic Exa Search. This phase consumes that decision; it does not
reinterpret the original experiment as passing its gate.

The exact tested contract is preserved in ignored
`local-evals/runs/dynamic-highlights-01/provider-contract.json`, `transport.py`,
and the historical `docs/operator/DYNAMIC_HIGHLIGHTS_01.md` on the prior
`codex/dynamic-highlights-01` branch. The preserved OpenAPI excerpt requires the
Dynamic beta header and says Dynamic/verbosity are incompatible with
`maxCharacters`. The experiment wrapper changed only the Search request.

## Production request

`search_exa(query)` posts to `https://api.exa.ai/search` with:

```json
{
  "query": "<ordinary Search query>",
  "type": "auto",
  "numResults": 6,
  "contents": {
    "text": false,
    "highlights": {
      "query": "<ordinary Search query>",
      "dynamic": true,
      "verbosity": "high"
    }
  }
}
```

The same request sends `Exa-Beta: dynamic-highlights-2026-08-28` alongside the
unchanged API-key and JSON content headers. No `maxCharacters` is sent. The
validated `result_count` argument remains available to callers; the ordinary
default remains six. Exa `/contents` does not receive the beta header or any body
change. The ordinary known-URL Read owner remains LinkUp static Fetch; Serper's
lexical/community/current Search route is unchanged.

## Custody and verification

The returned highlight strings are preserved verbatim. Distinct selections retain
`[Separate provider highlight; intervening context omitted]` between them.
Actual usable selections are `provider_highlights` Evidence; absent or malformed
highlights yield navigation candidates. Material over 65,536 characters retains
the existing omission and navigation behavior. No generated summary, local
reranker, runtime selector or downstream semantic contract was added.

Offline mocked request tests assert the complete Search body and headers, the
unchanged Contents body and headers, selection custody, navigation fallback,
ordering and size guard. Acquisition, novelty, Research-loop, catalog-table,
Answer/citation and full-suite checks establish the surrounding integration
boundary. No new live product, model or provider calls occurred in this phase.

This verifies the configured request and local custody behavior. It does not
establish universal answer quality, latency, cost improvement or future provider
behavior. The historical experiment report remains the bounded live evidence.
