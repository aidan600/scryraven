# Provider Capability And Acquisition Routing

Status: current
Authority: canonical:provider-capability-acquisition-routing
Default-read: yes
Applies-to: current ordinary acquisition routing, ProviderPlan projection, scheduling, and mechanical dispatch
Does-not-authorize: live calls, provider-quality claims, new adapters, cross-provider retry, or downstream evidence authority
Verified-against-runtime: 7626f1628a18bfb70c7abe58b120dc84001f2e71
Update-trigger: change to capability vocabulary, catalog, request derivation, provider selection, variants, or provider-material authority

## Purpose And Ownership

This document owns the current provider-capability and acquisition-routing
contract. `core.routing` is the sole provider-policy owner. It owns the immutable
capability catalog, deterministic request derivation, compatibility and
availability checks, ordered preference policy, typed route decisions, and typed
blocked decisions.

`core.provider_plan` records completed decisions. Retrieval scheduling,
dispatch, provider transports, and `run_pipeline()` consume those records
mechanically. They do not append, reorder, substitute, retry, or otherwise
select providers. Query production, ranking, recovery semantics, source custody,
evidence admission, Sufficiency, FinalAnswerPacket, and Author remain separate
owners and are unchanged by this routing foundation.

Runtime/test provenance:
`7626f1628a18bfb70c7abe58b120dc84001f2e71`.

## Capability Vocabulary

The installed acquisition capabilities are:

- `DISCOVER`: obtain URL-bound candidate/source material;
- `READ`: read a caller-selected known URL;
- `FOCUSED_EXTRACT`: extract material from caller-selected URLs against a
  bounded focus;
- `MAP_SITE`: enumerate a bounded site URL map;
- `CRAWL_SITE`: acquire a bounded set of pages from a site; and
- `PROVIDER_SYNTHESIS`: a vendor-written answer or report surface.

The installed `DISCOVER` qualifiers are:

- `general`;
- `domain_targeted`;
- `academic_technical_semantic`;
- `lightweight_disambiguation`; and
- `independent_index`.

Capabilities state what acquisition operation is required. Qualifiers narrow a
discovery role. Provider identity, product mode, generic complexity, retrieval
intensity, profile name, and caller metadata do not create a capability.

## Request Derivation

Ordinary `run_pipeline()` currently derives one `DISCOVER` request from already
existing deterministic facts:

1. an explicit bounded discovery-role qualifier wins;
2. the existing academic signal derives
   `academic_technical_semantic`;
3. a nonempty include-domain or exclude-domain constraint derives
   `domain_targeted`; and
4. otherwise the request is `general`.

News, currentness, comparison, quantitative status, report type, generic
complexity, and Fast/Balanced/Deep mode do not change provider identity or
activate a provider-specific variant. Domain constraints remain exact request
constraints; a domain such as `reddit.com` grants no social interpretation,
trust, representativeness, evidence, citation, or answer authority.

## Catalog And Decision Contracts

Each catalog entry records:

- provider, capability, qualifier, operation, variant, and output type;
- whether the vendor operation is known;
- whether an adapter is installed and ordinary-product enabled;
- current boolean availability and derived reachability;
- returned acquisition-material class; and
- authority posture.

The bounded availability snapshot contains booleans only for `tavily`,
`linkup`, `exa`, `serper`, and `brave`. It never stores credential values,
environment contents, raw diagnostics, or private material.

Each route decision records the request, selected provider/operation/variant/
output type, `exact` / `degraded` / `blocked` fidelity, descriptive fallback
candidates, decision or block reason, returned material class, provider-
synthesis-disabled posture, and social-authority posture. ProviderPlan may
retain its compatibility field `providers`, but it contains exactly one
provider or is empty.

Fallback candidates are descriptive only. Every fallback projection has
`dispatch_authorized=false`; scheduler and dispatch never consume fallback
candidates. Provider failure does not authorize a cross-provider retry in this
foundation.

## Installed Provider-Role Matrix

| Request | Exact selected implementation | Ordered degraded/fallback posture | Authority boundary |
| --- | --- | --- | --- |
| `DISCOVER(general)` | Linkup `search`, `standard/searchResults` | Tavily Search is the next descriptive compatible candidate | URL-bound non-authoritative acquisition material |
| `DISCOVER(domain_targeted)` | Linkup `search`, `standard/searchResults` with exact caller constraints | Tavily Search is the next descriptive compatible candidate | Constraints create no domain or social authority |
| `DISCOVER(academic_technical_semantic)` | Exa Search `neural_with_text/searchResults` | Linkup standard, then Tavily Search, are explicitly degraded candidates | Provider identity creates no academic truth authority |
| `DISCOVER(lightweight_disambiguation)` | Serper Web Search | None | Directional candidate material only |
| `DISCOVER(independent_index)` | Brave Web Search | None | Directional candidate material only |

Selection chooses the first installed, enabled, available, capability-compatible
implementation. If none exists, the result is typed `blocked`, its provider
projection is empty, and transport is not called. There is no phantom Tavily
fallback and no ordinary provider ensemble.

Overrides are ordered preferences, not fan-out requests. The router selects the
first compatible and available preference. An override containing no compatible
available implementation returns a typed blocked override decision; it does not
silently escape to ordinary policy.

## Provider Variants And Retrieval Intensity

Provider variants are distinct from generic retrieval intensity. Ordinary
Linkup discovery is explicitly `standard/searchResults` in Fast, Balanced, and
Deep. Complexity and search depth may still control generic retrieval work, but
they cannot promote Linkup to `deep`.

The existing Scrutineer remediation consumer is the only current ordinary
authorization for Linkup `deep/searchResults`. Its existing novel-query and
remediation gates remain unchanged. This is provider-extracted search-result
material, not provider synthesis, and it re-enters the existing downstream
path without special truth authority. General Linkup Deep activation remains
default-off and uninstalled.

## Provider Synthesis Closure

`PROVIDER_SYNTHESIS` is ordinary-product disabled. Cataloged Linkup sourced
answers/Research and Tavily Research cannot be selected by ordinary routing.
Provider synthesis remains disabled.
Provider-written answers, reports, or structured synthesis gain no source,
evidence, citation, Sufficiency, FinalAnswerPacket, or Author authority. The
retired ordinary Linkup `deep/sourcedAnswer` path remains retired.

## Installation Profiles

Profiles are diagnostic composition labels, not modes or routing
implementations. They grant no authority, create no fan-out, require no exact
provider set, and preserve arbitrary valid subsets:

| Profile | Illustrative available subset | Resulting installed roles |
| --- | --- | --- |
| Minimal | Linkup | General and domain-targeted Linkup standard discovery |
| Practical | Linkup + Serper | Minimal plus candidate-only lightweight disambiguation |
| Research | Linkup + Serper + Exa + Tavily | Practical plus exact academic/technical/semantic Exa and descriptive Tavily fallback |
| Diversity | Research + Brave | Research plus explicit candidate-only independent-index discovery |

Linkup-only remains valid. A profile name does not require every listed
provider, activate a disabled capability, or cause duplicate dispatch.

## Unavailable Catalog Entries And Future Adapter Sequence

The catalog deliberately represents known but unavailable operations:

- Linkup Fetch -> `READ`;
- Tavily Extract -> `READ` and `FOCUSED_EXTRACT`;
- Tavily Map -> `MAP_SITE`;
- Tavily Crawl -> `CRAWL_SITE`; and
- Linkup/Tavily vendor synthesis surfaces -> disabled
  `PROVIDER_SYNTHESIS`.

Requests for these capabilities return typed unavailable decisions and make
zero transport calls. The required implementation sequence is:

1. `KNOWN-URL-READ-FOUNDATION-01`: shared `READ` contract and Linkup Fetch
   first;
2. `TAVILY-EXTRACT-AND-MAP-ADAPTERS-01`: `FOCUSED_EXTRACT` and `MAP_SITE`;
3. `TAVILY-BOUNDED-CRAWL-ADAPTER-01`: bounded crawl caps and lineage;
4. `LINKUP-DEEP-SEQUENTIAL-ACQUISITION-01`: bounded, default-off premium
   `deep/searchResults` without mode/complexity activation;
5. `ACQUISITION-ROUTING-CLOSURE-01` if residual provider-name owners block the
   ordinary capability consumer;
6. bounded final-custody convergence;
7. separately licensed comparative live validation;
8. separately designed social-source authority and Social Awareness; and
9. transport-neutral conversation/UI work.

Product mode and generic complexity must not trigger general Linkup Deep.

## Residual Compatibility Owners

The current ordinary `run_pipeline()` path always supplies ProviderPlan's
single selected provider. A lower-level `core.pipeline.process_search_queries`
compatibility path still accepts `search_providers=None` and retains provider-
name/complexity behavior. Legacy saved-thread follow-up and explicit
operator/validation provider decisions also retain provider-specific surfaces.
They are not ordinary route owners and remain candidates for the bounded
acquisition-routing closure only if they block a later ordinary consumer.

## Nonproofs And Closed Surfaces

This offline foundation does not prove live provider quality, coverage,
currentness, latency, cost, reliability, or empirical best-provider status. It
does not install Linkup Fetch; Tavily Extract, Map, or Crawl; general Linkup
Deep; provider-failure fallback execution; provider ensembles; social
interpretation; or a provider-written synthesis path.

It changes no query semantics, prompts, ranking, recovery decision, source
obligation, source custody, evidence correctness, citation eligibility,
Sufficiency, FinalAnswerPacket, Author behavior, persistence, conversation, UI,
or answer quality. No live provider, model, search, fetch/read, or retrieval
call was performed by the foundation proof.
