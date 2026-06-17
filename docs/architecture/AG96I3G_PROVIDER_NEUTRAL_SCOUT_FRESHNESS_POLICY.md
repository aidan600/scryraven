# AG-96I3G Provider-neutral Scout Freshness Policy

## Status

AG-96I3G adds an offline freshness policy diagnostic helper and moves the
AG-96I3E Brave diagnostic path onto a provider-neutral scout wrapper. AG-96I3H
adds Serper to that same scout wrapper as a cheap candidate-discovery surface.
No live validation was run and no broker was started for either freshness policy
work or the Serper adapter.

The implementation surfaces are:

```text
core.followup_search_freshness_policy
core.search_providers.search_scout_results
scripts/ag96i3e_brokered_provider_neutral_discovery_validation.py
```

The helper emits sanitized diagnostics only. It does not call providers,
fetch/read pages, inspect `.env`, read secrets, invoke models, activate Author,
or create citation-eligible evidence.

## Why Past-week Brave Freshness Was A Confound

After AG-96I3F, the shaped query:

```text
IRS 2026 standard mileage rates business use car notice announcement
```

was run manually through the existing Brave scout wrapper. The top results
remained secondary or SEO-style, and no official/current IRS candidate surfaced.
That result was confounded because the wrapper hardcoded Brave
`freshness="pw"`.

Past-week-only freshness can favor recently updated explainers over canonical
official artifacts. For an official/current known-year fact, the canonical
source may have been published weeks or months earlier and still be the current
authority.

## Freshness Is A Search-job Prior

Freshness is not "more recent is always better." It is a retrieval prior:

```text
When would the canonical source likely have been published or last updated?
```

The prior belongs to the scout/search job, not to a provider wrapper. A provider
surface may have its own syntax for recency, but the job decides whether recency
is helpful, harmful, broad, narrow, mixed, or absent.

Examples:

- IRS 2026 mileage rate: known-year/current official artifact. Past-week-only
  freshness is forbidden for the diagnostic scout policy.
- Latest patch notes: recent-ish, but the latest patch may be weeks or months
  old, so past-week-only should not be forced.
- Market news today: narrow freshness is appropriate.
- Historical or stable facts: provider freshness should usually be absent.

## Provider-neutral Scout

Scout is the role. Brave and Serper are provider surfaces that can perform the
role. Later APIs can plug into the same scout/freshness contract without
renaming the role or treating one provider as the model.

AG-96I3G introduces:

```text
search_scout_results(provider=..., query=..., freshness_policy=...)
```

Today this generic wrapper supports `provider="brave"` and `provider="serper"`.
The legacy `brave_reconnaissance(...)` function remains as a compatibility
alias and keeps its historical default. New diagnostic code uses the
provider-neutral scout path instead.

Serper receives Google-style `tbs` freshness values only when the
provider-neutral policy chooses recent/breaking freshness:

- `latest_breaking` and `recent_days`: `qdr:d`;
- `recent_weeks`: `qdr:w`;
- `recent_months`: `qdr:m`.

Known-year, current-year, current-or-stable, historical-or-stable, and
mixed-probe postures omit Serper freshness so official/current artifacts are
not accidentally narrowed out.

## Diagnostic Runner Contract

The AG-96I3E brokered runner now includes:

```text
freshness_policy_diagnostics
```

The packet records:

- freshness intent;
- freshness window;
- provider freshness policy;
- provider freshness value by provider;
- whether over-narrow recent freshness is forbidden;
- whether mixed probes are allowed;
- closed-surface flags;
- evidence boundary flags.

The runner still preserves:

- one provider/search call budget;
- max-results cap;
- `discovery_unconstrained` behavior;
- no `includeDomains` or `site:` filters;
- no fetch/read;
- no model calls;
- no Author calls;
- sanitized output under ignored `output/` paths only.

## Evidence Boundary

Freshness policy diagnostics and selected search candidates are diagnostic
observations only. They are not final evidence and are not citation eligible.
Final evidence still requires a later, separately authorized fetch/read and
admission phase through the existing authority chain.

## Serper Diagnostic Boundary

AG-96I3H implements Serper as the next cheap scout adapter. Serper output is
diagnostic only, not final evidence and not citation eligible. It is useful for
future multi-query fan-out over AG-96I3F-shaped variants, but that fan-out still
requires explicit authorization. Premium provider work or fetch/read may still
be needed after Serper finds a promising candidate.
