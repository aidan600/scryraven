# ScryRaven Current Truth

Status: research efficiency and evidence-feedback phase meets bounded acceptance
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Implemented product path

PRODUCT.md remains the approved charter. The authorized multi-component extension
and research-efficiency work use `python -m scryraven "<public-web question>"`.
Semantic owners remain Research -> Analyst -> Author, followed by mechanical
citation resolution. No planner, source-quality owner or alternate product path exists.
Both FAST (Research/Author) and SMART (Analyst) remain gpt-5.6-luna / medium,
independently configurable, with no fallback. The doorman remains operator-only
secret custody/process plumbing; the product does not import it.

Research orients to provisional answer needs, appropriate publishers, material
sought and temporal requirements. The original question governs. Orientation and
source expectations remain revisable, run-local model judgments. One source may
address multiple components. No component graph, scheduler, authority registry,
source score, domain admission list or freshness window exists. Current/applicable
is distinct from recently published. Secondary sources can explain, corroborate,
guide navigation or provide the best obtainable evidence.

Research chooses Standard Discover, direct read of an existing candidate, or done.
The unused Linkup Fast Scout experiment and its exclusive transport/schema/counter/
prompt/test machinery were removed. No provider or routing layer was added.
Discover requests at most six candidates by default. Normal returned context is
preserved whole with internal whitespace, replacing the old 500-character clip.
No provider content-length maximum is documented. Above 65,536 characters the
entire context is explicitly omitted with a notice and original size, retaining
its URL for Fetch. Safe traces expose identities, sizes and omissions, not full
navigation context. Discovery remains navigation, never answer evidence.

Each run-local semantic need permits at most two Standard Discover calls initially.
Failed calls spend allowance. Actual acquired evidence must reach Analyst, which
must identify a specific materially unresolved same-need gap, before one second
round opens. It permits at most two additional Standard calls. Unused initial
allowance expires. Assessment of new evidence in round two closes remaining search
allowance for that need; useful existing reads survive. There is no third return.
These bounds are ceilings, not targets. No runtime fuse was raised.

Analyst reuses need references for equivalent gaps, narrower searched portions,
source-route changes and continuing temporal needs. Genuinely new missing meaning
requires an explicit explanation before mechanics assign another reference.
Semantic identity remains fallible: an erroneous new-need judgment could allocate
allowance. Wording or component changes alone cannot reset the counters.

Candidates and compact attempts survive follow-ups. Exact URL duplicates keep
their aliases and may receive refreshed returned context. Search hypotheses explain
expected evidence, novelty, value, acquisition prospects and why promising unread
candidates cannot address the gap. Research selects small sets by distinct expected
contribution, considers source-size clues when present, and can recover a failed
publication through another justified search within existing bounds. It need not
read weak leftovers merely to avoid discovery. This is semantic guidance, not a
numeric scoring system or a guarantee against poor reads.

Only successful direct Fetch creates immutable E-ID evidence with source URL,
title and readable text. Exact acquired URLs are not fetched again. All acquisitions
remain in memory. Research relevance selection inspects new bodies and Analyst's
previous findings/gap, omits irrelevant or redundant material, and can restore older
IDs. Later navigation sees candidate context, acquired metadata, compact attempts,
the previous assessment and the recent relevance selection.

Research may nominate a small useful set of explicit links found in actually
acquired text. Mechanics validate source identity, public-URL syntax and occurrence,
resolve relative links, and encode spaces. Each malformed or invalid optional item
is rejected with a fixed safe diagnostic without losing valid siblings, candidates
or acquired evidence. The destination still requires Fetch. There is no automatic
traversal, crawler, invented URL or model-memory link admission.

The provisional outer limit is three Analyst assessments, each preceded by at most
six navigation actions. Initial irrelevant reads continue within that same remaining
allowance; empty evidence reaches Analyst only at genuine initial exhaustion.
Unchanged immutable evidence retains the prior Analyst assessment even if provisional
needs change. Omitted reads do not consume an Analyst pass, reset navigation, or earn
another search round. Newly relevant evidence reaches Analyst at a bound.

Analyst assesses the whole question, selected acquired bodies, provisional needs,
previous analysis and compact discovery history. Prior support and active conflict
context survive triage; Analyst can revise their role. Findings reference submitted
evidence. Author receives supported findings, qualifications and supporting sources.
Code validates references and resolves citations, not semantic support. Supported,
partial and unable postures exit 0; execution errors exit 1.

## Demonstrated outcome and limits

Final runtime bdf17e30f292d24b0f77f15203a096ba35ed1f3e was exercised through the ordinary
entrypoint, actual model/Linkup path and Author/citation consumer for the exact canary,
Saturn and Galloway questions. Later delivery changes are documentation only.
The phase meets its bounded quality/evidence/efficiency criteria; universal reliability
or an unqualified latest-event answer is not demonstrated.

| Final observation | Standard by round | Fetch attempts / acquired | Acquired characters | Analyst calls | Result |
| --- | --- | --- | --- | --- | --- |
| Maximum ten-pin bowling ball weight | 1 / 0 | 2 / 2 | 186,063 | 1 | Supported 16.00 pounds under USBC specifications. |
| September 2026 Saturn 274/285/293 reconciliation | 1 / 0 | 6 / 6 | 168,766 | 3 | Supported, scoped 293 from NASA and JPL; older conflicting text and March count explained. |
| latest Scott Galloway controversy | 1 / 0 | 5 / 5 | 78,829 | 3 | Qualified account; compared dated incidents, with weak corroboration and latest status explicitly unresolved. |

The final canary acquired the USBC equipment manual directly from a search candidate.
It matches PR #626's one search, two reads and one Analyst call. Acquired characters
are 3.6% higher because the fetched manual differs, but triage omitted the redundant
tournament rules before Analyst, reducing source-body submission across models by
9.2%. An earlier continuation canary followed an explicit link from an acquired
explanation to this same governing manual without another Discover. Final-runtime
Saturn and Galloway also demonstrated acquired-link navigation.

Saturn read the visible NASA moons page, followed its explicit link to JPL's inventory,
and acquired the IAU March announcement, its linked MPC circular, a 2023 newsletter
and a recent-MPEC index. It recovered authoritative 293 evidence and did not miss a
promising visible current-count candidate. Compared with PR #626: three searches
became one, nine reads became six, and 355,967 acquired characters became 168,766
(52.6% fewer). Total source-body characters submitted across Research triage, Analyst
and Author fell from about 1.42 million to 735,000 (48.3%). These are body counts,
not measured tokens, price or latency.

NASA's acquired page reported 293 as of August 2026 while also containing older
274 text. The linked JPL inventory stated 293 officially recognized Saturn satellites;
IAU supplied the March 285 total. This is stronger aggregate/currentness evidence than
PR #626's NASA APOD June statement. The answer qualifies the September cutoff and
does not certify future changes or reconstruct every addition. Inconsistent page
metadata remains visible. The 2023 newsletter and repeated March detail were weak
selections; selectivity improved but is imperfect.

Galloway compared a reported August property-database dispute, later SpaceX valuation
comments and older Hollywood criticism. It acquired a linked commentator post and
the original Business Insider article after its republication. Two invalid optional
links were rejected while valid links/evidence survived. It skipped a wrong-person
candidate and avoided a search loop. The result attributes the principal allegation
to a partisan report, does not independently establish it, and does not assert a
definitive latest incident. Relative to PR #626: three searches became one; Fetch
attempts remained five (five successes versus four); bodies fell from 180,573 to
78,829 and model source-body submissions from 570,519 to 254,046. Primary responses
and latest-event completeness remain unproved. No particular historical controversy
was required for acceptance.

The first six PRODUCT invocations were exhausted with acceptance NOT MET. The
authorized continuation used five additional PRODUCT invocations, zero of four
additional retrieval-only probes, and three additional reviewer source checks.
The earlier four probes compared Fast/Standard on Galloway and Saturn; Fast was
never chosen in the first six PRODUCT runs. Standard already exposed Galloway's
incident terrain; Saturn probe candidates were identical. No demonstrated failure
required Scout, so it was removed instead of retained through its tests.

Reviewer checks confirmed the USBC 16-pound passage and NASA/JPL's 293 statements.
Reviewer evidence never entered the product corpus. No optional transfer was run;
the three priority observations were sufficient to decide this bounded phase.
Credentials, private environment values and raw provider payloads were not inspected.
Sanitized answers, traces, selected supporting evidence, comparisons and the full
review bundle remain outside the repository at
`C:\tmp\scryraven-research-scout-feedback-loop-01\continuation`.

## Offline verification and architectural frontier

Final full pytest passed 123 tests; focused checks, Ruff, pre-commit, production
imports/AST and git diff --check passed. CI remains offline and unchanged, with no
provider calls or credentials. Scenarios exercise full >500-character context through
the transport and CLI, visible pathological omission, non-evidence separation, hard
2+2 bounds, earned feedback, no third return even with unused allowance, failure
accounting, need-reference continuity, candidate reuse, and evidence preservation.

The landing-page -> explicit manual link -> Fetch -> Analyst scenario needs no
additional Discover. Mixed valid/malformed/invalid nominations retain valid links
and evidence; malformed URLs already in a source cannot break nomination. Tests
cover omitted reads before the first Analyst and after feedback, including revised
provisional needs, without resetting navigation or repeating Analyst input. Scripted
judgments demonstrate mechanics, not general semantic competence.

NO EMBEDDINGS NOW. Search repetition, candidate clustering, semantic duplicates,
need continuity and Scout triage were evaluated against the observed failures.
Existing context/history and semantic judgment are simpler for these small candidate
sets. Similarity does not establish source ownership, currentness, independence or
support; no saved retrieval/model call was demonstrated. No embedding API, vectors,
vector database, persistent state or similarity authority was added.

Large-document reading remains deferred: no PDF chunks, embeddings, passage indexes,
targeting, compression or IPCC run. The earlier IPCC pulse acquired approximately
845k/893k characters before model_rate_limited; context overflow was not established.
Deterministic calculation remains absent; the prior incidental NASA radius calculation
error was not addressed. Earlier golf, Pluto/IAU and Webb demonstrations used earlier
revisions/defaults and are not final-runtime guarantees.

Source selection, scope/currentness judgment, candidate availability, semantic need
identity and model-generated citations remain fallible. Additional retrieval can
still be warranted before a read batch, and even relevant new detail can close the
last search round without resolving the gap. The final runs establish an improved
tradeoff, not an optimal minimum or a measured causal effect from richer context alone.

Exactly Research, Analyst and Author retain semantic authority. Persistent sessions,
resumability, parallel research, provider routing/fallback, generic recovery and
semantic compression remain absent. Old v1 machinery, the 500-character semantic
clip, exceptional-third-search machinery and Scout-only machinery are removed.
This outcome does not authorize merge, aftercare or beginning another capability.
