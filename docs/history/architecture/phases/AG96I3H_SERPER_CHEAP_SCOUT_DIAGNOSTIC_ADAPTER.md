Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3H_SERPER_CHEAP_SCOUT_DIAGNOSTIC_ADAPTER).

# AG-96I3H Serper Cheap Scout Diagnostic Adapter

## Status

AG-96I3H adds Serper as a cheap scout/candidate-discovery provider surface
behind the provider-neutral scout API:

```text
core.search_providers.search_scout_results(...)
```

No live validation was run, no broker was started, and no Serper, Brave,
Tavily, Linkup, Exa, OpenAI, fetch/read, model, Author, citation,
EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, or product answer
behavior was invoked.

## Provider Role

Serper is a scout surface only. It may provide search-result observations such
as title, URL, snippet, domain, credibility, position, and date-style SERP
metadata. It does not admit final evidence, create citation eligibility, fetch
or read pages, call models, activate Author, or change product routing.

The role remains provider-neutral:

```text
Scout is the role. Serper is one provider surface for that role.
```

This phase does not create a Serper reconnaissance role and does not route
product behavior through Serper.

## Adapter Shape

The adapter uses the documented Serper Google Search API shape:

- `POST https://google.serper.dev/search`
- `SERPER_API_KEY` from the environment, sent as `X-API-KEY`
- JSON request with `q` and `num`
- optional Google-style `tbs` only when the provider-neutral freshness policy
  supplies one
- response `organic[]` fields normalized from `title`, `link`, `snippet`,
  `position`, and optional `date`

The normalized result dictionaries retain only sanitized diagnostic fields:

- `title`
- `url`
- `snippet`
- `domain`
- `credibility`
- `position`, when positive integer-like
- `date`, when string-like and bounded

Raw provider payloads, response bodies, sitelinks, page text, keys, prompts,
model outputs, DB/cache rows, private logs, and full traces are not retained.

## Brokered Runner

`scripts/ag96i3e_brokered_provider_neutral_discovery_validation.py` now accepts:

```text
--provider serper
```

The runner dispatches Serper through `search_scout_results(provider="serper",
...)`, preserving the AG-96I3E live budget:

```json
{
  "max_provider_search_calls": 1,
  "max_fetch_read_attempts": 0,
  "max_model_calls": 0,
  "max_author_executor_calls": 0,
  "retries_allowed": false
}
```

The runner still refuses live provider mode without
`--confirm-live-provider-call`, checks only for the `SERPER_API_KEY` key name,
caps `--max-results`, keeps `discovery_unconstrained`, passes no
`includeDomains`, and writes only sanitized packets under ignored `output/`
paths.

## Freshness Policy

Freshness remains a search-job prior owned by
`core.followup_search_freshness_policy`, not by Serper.

Serper receives no narrow freshness for known-year, current-year,
current-or-stable, historical-or-stable, or mixed-probe postures. For
recent/breaking postures, AG-96I3H maps the provider-neutral policy to
Google-style `tbs` values:

| Freshness intent | Serper request value |
| --- | --- |
| `latest_breaking` | `qdr:d` |
| `recent_days` | `qdr:d` |
| `recent_weeks` | `qdr:w` |
| `recent_months` | `qdr:m` |

The IRS known-year shaped query remains broad:

```text
IRS 2026 standard mileage rates business use car notice announcement
```

That query does not add Serper `tbs`.

## Future Use

Serper is useful for later explicitly authorized multi-query fan-out over
AG-96I3F-shaped variants because it is cheap and returns Google-style candidate
observations. That fan-out is not implemented in this phase.

A premium provider or a later fetch/read/admission step may still be needed
after Serper finds a promising candidate. Serper discovery by itself is not
evidence and is not citation eligible.

## Closed Surfaces Preserved

AG-96I3H does not change:

- product provider routing;
- provider selection policy;
- product query generation;
- fetch/read behavior;
- model calls;
- Author or citation behavior;
- EvidenceLedger authority;
- SufficiencyJudgment authority;
- FinalAnswerPacket authority;
- `core/pipeline_orchestrator.py` domain logic;
- include-domain or `site:` filtering;
- source-specific IRS resolution.
