# AUTHOR-PROSE-ONLY-FINALIZATION-01

Status: Completed implementation posture for the RunKernel-owned prose-only
finalization surface after hardened FinalAnswerPacket.
Verified-against-runtime: 4e095c7db287ab29fbe748bdd5c24cf4f2545e15

## Purpose

AuthorProseFinalization is the prose-only finalization surface and consumes hardened FAP only,
plus an AuthorProsePolicy, and emits adjustable,
human-readable prose without changing answer authority.

The surface exists so answer presentation can improve over time: style,
formatting, brevity/detail, source-pass-through presentation, caveat handling,
partial-answer feel, blocked-answer feel, contested-answer feel, and
insufficient-evidence feel can all be tuned without upgrading FAP truth,
status, citation, source-obligation, or product-correctness posture.

## Runtime Path

The runtime path is `core/author_prose_finalization_runtime.py`, with policy
normalization in `core/author_prose_policy.py`. RunKernel authorizes
`AUTHOR_PROSE_FINALIZE` at `author_prose_finalization`, reduces
`AUTHOR_PROSE_FINALIZED`, and writes only:

- `state.author_prose_state`
- `state.author_prose_projection`
- `state.author_prose_history`
- `state.projections["author_prose_finalization"]`

It requires existing `state.final_answer_authority_projection`, binds the FAP
packet digest or no-packet digest, binds the final-answer authority projection
digest, binds the policy digest, and rejects stale FAP/projection/policy
bindings during reduction.

Before any AuthorProse state or projection is created, the shared deterministic
quantitative finalization validator binds every numeric assertion to the
hardened FAP manifest. A rejection creates no successful AuthorProse state,
does not edit the prose, and does not invoke a model retry.

AuthorProseFinalization does not write canonical output to legacy `author_observation` / `final_answer_outcome`.
It also does not mutate `current_answer_contract`.

## Policy Knobs

AuthorProsePolicy exposes style/format/brevity/source-pass-through/uncertainty
knobs, plus partial-answer, blocked-answer, and citation-display presentation
knobs. Defaults are mode-aware:

- Fast: terse, direct, minimal refs.
- Balanced: normal, answer-then-evidence, evidence summary.
- Deep: detailed, research note, source appendix.

Policy may change prose form, but it must not change FAP authority posture.

## Output Taxonomy

Author prose status maps directly from hardened FAP status:

- `full_answer_packet_ready` -> `full_answer_prose_created`
- `partial_answer_packet_ready` -> `partial_answer_prose_created`
- `blocked_answer_packet` -> `blocked_answer_prose_created`
- `followup_required_packet` -> `followup_required_prose_created`
- `contested_answer_packet` -> `contested_answer_prose_created`
- `insufficient_evidence_packet` -> `insufficient_evidence_prose_created`
- `not_applicable` -> `not_applicable_no_answer`

No status is upgraded by AuthorProseFinalization.

## Status Behavior

For full-ready FAP, prose may state supported components as supported while
preserving mandatory caveats and prohibited upgrades. If hardened FAP lacks safe
claim text, prose says so and uses component labels/identifiers rather than
reaching around FAP.

For partial FAP, prose separates supported parts from unresolved parts and does
not imply a full answer.

For blocked FAP, prose explains the blocker only and does not answer unsupported
components.

For follow-up-required FAP, prose explains that remediation/follow-up is still
required. It does not authorize follow-up and does not imply remediation is
complete.

For contested FAP, prose preserves contested posture and does not smooth
disagreement into fact.

For insufficient-evidence FAP, prose says evidence is insufficient and creates
no supported claims.

For `not_applicable`, prose creates a safe no-answer projection only, with no
normal answer text beyond a status message and no supported claims.

## Citation And Source Boundary

AuthorProseFinalization may present source support refs as refs/digests, support
ref placeholders, evidence summaries, or source appendices. These are support
refs, not rendered citations.

It does not render citations, does not create citation eligibility, and does not satisfy source obligations.
It does not claim product correctness. The
projection keeps `citation_eligible: false`, `citations_rendered: false`,
`source_obligation_satisfied: false`, and `product_correctness_claimed: false`.

## Dogfood Conformance

`core/author_prose_conformance_runtime.py` adds
AuthorProseConformanceReview as dogfood/testing-only. It is deterministic and
offline, emits `conformance_passed`, `laundering_suspected`, or
`blocked_for_review`, and checks that prose stayed within the hardened FAP.

AuthorProseConformanceReview is dogfood/testing-only, not production-blocking.
It does not call models/providers/search/retrieval/fetch/read, old Author, the
pipeline orchestrator, citation rendering, or source-obligation machinery.

## Closed Surfaces

This phase does not call a model or provider, does not execute old Author, does
not assemble old prompts, does not render citations, does not satisfy source obligations,
does not claim product correctness and does not mutate current_answer_contract.
It does not access raw/private/unbounded data.
