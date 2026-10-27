# Citation Previews and Editorial Restraint 01

Status: local implementation and offline editorial correction complete; prior live editorial observations mixed; corrected prompt not live-tested; not deployed.

Production base: `33511b268d9b07ab10bc0725d488132fb5e3f324`.
Branch: `codex/citation-previews-editorial-01`.

## Frozen ordinary-product observations

The first two questions and expectations were fixed before any submission; the
third was fixed after the first result and before its own submission.
They exercise the ordinary Reading Room HTTP submission, production Research
and Answer, acquired originals, durable store and rendered citation consumer.
The existing credential doorman supplies the personal ChatGPT-plan backend;
shipped Luna/high Research and Sol/medium Answer remain unchanged. No API
inference fallback or independent public-source check is allowed.

1. **Compact factual lookup:** “What professional experience does Dimitrios
   Zografos describe in his official candidate statement, and had he previously
   held elected or appointed public office?”
   Expect the actual statement's identity and chronology to control the answer.
   Report the scoped experience and office history directly, without a routine
   independent-verification disclaimer. Each preview should describe the cited
   material's contribution and respect whether only highlights were supplied.
2. **Substantive comparison:** “What does the published evidence say about
   Waymo rider-only vehicles’ safety compared with human drivers, and how far
   does that evidence support choosing robotaxis over public transit?”
   Expect a useful comparison preserving operational exposure, comparison
   populations and crash-rate denominators. Distinguish evidence about human
   driving from evidence comparing transit and robotaxis. Keep consequential
   distinctions while avoiding repetitive caution. Several distinct citations
   should have short, source-specific, faithful previews.

3. **Compact factual control, frozen after the first result and before its own
   submission:** “Who received the 1921 Nobel Prize in Physics, and what
   achievement did the official prize citation recognize?” Expect a direct
   recipient/achievement answer grounded in the actual official record, with a
   useful source-specific preview and no unsolicited qualifications. The Zografos
   draw did not locate an identifiable statement, so it covers uncertainty while
   this third submission completes the originally approved compact-lookup check.

Phase ceilings are three ordinary submissions, 30 physical model requests,
24 external acquisition attempts and zero independent public-source checks.
The first submission received at most 12 physical requests and eight external
attempts through existing RunLimits. It used seven physical requests and eight
external attempts. The comparison receives at most 18 physical requests and 14
external attempts, reserving up to five physical requests and two external
attempts for the compact factual control. These observation
limits are development configuration, not new product policy or stored state.

Evaluate preview usefulness, source fidelity, original-publication access,
saved excerpts, editorial quality, output size and Answer latency. Three qualitative
draws cannot establish statistical improvement, and no paired baseline latency
measurement is planned. Historical pre-promotion prose is not a baseline.

## Outcome and tested revision

Citation previews are implemented and demonstrated through the ordinary product.
The approved Answer editorial principle is implemented; its qualitative result is
mixed. The compact lookup is direct and economical. The comparison preserves
consequential distinctions but still contains unnecessary caution and repetition.
Consistently restrained prose and a causal improvement over merged behavior are
not established by these unpaired draws.

Full-offline and ordinary-product tested implementation:
`65a230a1c14e2b4696f525fb42c57f3dac3fb903`. The current branch additionally contains
the focused editorial prompt correction below, verified only offline. All complete
product outputs, screenshots and latency observations in this report predate that
correction. The final delivery identifies the current local head.

## Focused editorial correction

The human authorized one prompt correction on the clean existing branch at
`6f329713ac88e4a685b45132ce13c3e82b98a0a4`, with no further live calls or experiment.
The concrete failure is the current 65a230a Waymo response reproduced below:
it repeats the transit nonconclusion in the opening, section heading/lead and
conclusion, and appends zero-risk, independent-replication and broad extrapolation
cautions after establishing the findings' relevant scope. Vehicle/passenger-mile,
crash/claim and substitution distinctions remain substantive analysis to preserve.

Inspection covered the actual entire Answer prompt, including its source,
highlight, PDF and delivery limits. Those grounding constraints remain intact.
The follow-on writing paragraph's unconditional comparison checklist lacked a
clear distinction between applying such constraints to claims and narrating them.
It also lacked guidance against repeating a controlling limitation throughout.

One paragraph now directs appropriately scoped findings and analysis of material
consequences, omits generic or obvious qualifications that do not change the
answer, and revisits an overarching limitation only for a consequential new
distinction or revised conclusion. The original governing principle, analytical
depth, source grounding, chronology, critical judgment, competing evidence,
supported calculations and honest partial/unable answers remain. The patch does
not change Research or any citation-preview generation contract, matching,
validation, persistence or browser interaction. No length target, word prohibition,
detector, style test framework or additional model stage was introduced.

Exact prompt diff against `6f32971`:

```diff
@@
 Give the conclusion or controlling distinction early and use a format suited to
 the question. Develop the reasoning, important relationships and representative
-support needed for a useful answer. Preserve consequential competing evidence.
-In comparisons, keep units, populations, scope and observed-versus-modeled status
-clear. Explain how quantitative inputs determine the result.
+support needed for a useful answer. Apply grounding, provenance and acquisition
+limits when scoping claims; they are not a checklist of disclosures. Explain
+material distinctions through their consequences for the question. Do not append
+general disclaimers, obvious logical qualifications or statements about what a
+source cannot prove when they do not change the answer. Once an overarching
+limitation is established, continue the analysis without repeating it across the
+introduction, individual sections and conclusion; revisit it only to add a
+consequential distinction or revise the conclusion. Preserve consequential
+competing evidence and honest partial answers. In comparisons, integrate the
+units, populations, scope and observed-versus-modeled basis needed to interpret
+the result into the analysis. Explain how quantitative inputs determine the result.
```

The correction passed 241 applicable existing offline tests, Ruff, Python
compilation, whitespace checks and all six configured hooks. Tests exercise native
delegation, briefing, grounding/posture contracts, citation correction, previews,
premise-only answers, calculation, model transports/cache layout, retained sources
and durable sessions through scripted I/O. No exact-prose test was added.
An independent read-only review found the change confined to that editorial
paragraph and preserving the surviving obligations. These checks establish
mechanical compatibility, not editorial improvement. The corrected prompt has no
new live evidence. Earlier outputs and evaluation gold were not rewritten.

## Implementation and removal

The final Answer's existing strict JSON response adds nullable
`citation_descriptions: [{source_ref, description}]`. Required primary fields,
source-grounding validation and the existing citation-correction allowance remain
strict. A local before-validator accepts absent metadata and discards malformed
entries; valid neighbors survive. Empty/overlong descriptions are unusable display
metadata and are discarded. The 1,200-character usability bound applies to preview
metadata, not to Answer length. The prompt normally requests one or two sentences.

After final prose validation, the existing selected-material alias map matches
descriptions to actually used canonical source identities. Unknown, unavailable,
unsupplied or uncited references cannot establish membership. First usable
description wins for a source. Repeated references and multiple actual acquired
versions/excerpts reuse that source's description without changing exact material,
original URLs, numbering or CitationUse offsets.

One nullable `Citation.description` field persists through the existing JSON turn
record in SQLite schema 2. Absence remains omitted when writing historical records;
no migration, backfill or model invocation is needed. Description text does not
enter Evidence, future Research context or body-free diagnostics. It is escaped
at the presentation boundary. No changes to model routing, Research's prompt,
session orchestration or an independent semantic owner were needed.

Reading Room uses the existing source body renderer and original-link safety
checks. Validated inline links retain exact web URLs with separate-tab and
noopener/noreferrer behavior. The compact preview opens on hover/focus and on
touch tap; Tab/ArrowDown/Space enters its actions, Escape dismisses/restores focus,
and outside interaction dismisses it. View saved excerpt opens native inline
details, with exact saved text, acquisition labels and historical support context.
Original session-owned PDFs remain available. Without JavaScript, direct web links
and expandable Sources/saved excerpts remain accessible.

Removed completely: full-height evidence-inspector dialog, desktop docking,
laptop overlay/mobile sheet layouts, source-overview/back-navigation controller,
unused back icon and obsolete inspector assertions. Evidence custody, immutable
versions, citation-use records, historical support coordinates, durable sessions,
PDF bytes and source reopening remain. No removed inspector machinery remains.
Explicit removal: complete.

The governing Answer passage is:

> Answer the user's question directly and fully at the scope the evidence supports.
> State findings accurately without routinely explaining obvious limitations or
> enumerating what the sources do not establish. Include qualifications when they
> materially change the conclusion, resolve a genuine ambiguity, or identify a
> consequential unanswered part of the request. Assume the reader can understand
> ordinary provenance and context.

It continues that recognizing a limitation does not automatically require
narrating it, and prefers properly scoped claims over overbroad claims followed
by defensive explanation. The soft two-page ceiling and repeated missing-input
qualification instructions were removed. Grounding, chronology, identity,
competing evidence, calculation, honest partials and independent judgment survive.
No lexical filter, mandatory outline or arbitrary Answer length was introduced.

## Ordinary-product evidence

All three questions ran through browser form submission -> Reading Room ->
ResearchSession -> production Research/Answer -> SQLite -> reopened browser UI.
The approved personal plan backend and shipped explicit model configuration were
injected through the existing application seam using the existing doorman.
No paid API inference fallback occurred.

| Draw | Posture | Physical requests | External attempts | Product seconds | Physical Answer seconds | Answer / preview characters |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Zografos identity boundary | Unable | 7 | 8 | 71.265 | 11.781 | 312 / 0 |
| Waymo comparison | Supported | 7 | 7 | 127.063 | 59.579 | 5,501 / 896 |
| Nobel factual control | Supported | 3 | 1 | 17.250 | 5.390 | 218 / 98 |
| **Total** | | **17** | **16** | **215.578** | | |

Phase usage: **three submissions, 17/30 physical requests, 16/24 external attempts,
zero independent public-source checks**. No further submission is licensed or
implied by unused request/acquisition allowance. Neither role needed a shape or
citation correction in these draws. Waymo used one native delegated Research
episode and returned to the same Answer interaction; its 101.454-second Answer
interaction includes 41.875 seconds of delegated Research. The initial unable
answer also used native local inspection before declining to identify a candidate.

Preview metadata adds 98 characters for the compact answer and 896 across seven
comparison sources, plus JSON framing. It adds no dedicated model interaction.
The compact Answer completed in 5.390 seconds; the substantive Answer's physical
requests took 59.579 seconds. There is no paired current-main baseline, so neither
a latency increase caused by previews nor an improvement can be isolated.
Comparison latency and verbosity remain noticeable product limitations.

Launch/capture issues were operational, with no extra submissions: preflight
stopped before serving because effective user model settings differed from shipped
settings; the observation launcher then explicitly injected the approved shipped
configuration. The first browser driver's default navigation timeout expired
after dispatch, while the server continued and saved its result. The comparison
browser later reported `ERR_NO_BUFFER_SPACE` after the server committed. Both
answers reopened successfully; neither question was resubmitted. Browser capture
recovery required no code change or provider request.

## Complete current-product answers and previews

The following answers and descriptions are verbatim generated outputs. Source
numbers are local to each answer. Publication links below are the immutable saved
URLs; no external publication was independently opened during evaluation.

### Zografos identity boundary

Question: What professional experience does Dimitrios Zografos describe in his official candidate statement, and had he previously held elected or appointed public office?

> I couldn’t reliably identify Dimitrios Zografos’s official candidate statement, so I can’t confirm what professional experience he described or whether he had previously held elected or appointed public office. Please share the statement—or the election’s location and year—so I can answer both parts accurately.

No citations or generated previews; the answer does not claim an externally supported finding.

### Waymo comparison

Question: What does the published evidence say about Waymo rider-only vehicles’ safety compared with human drivers, and how far does that evidence support choosing robotaxis over public transit?

> **The evidence supports a substantial safety advantage for Waymo’s rider-only vehicles over human-driver benchmarks in the settings studied. It does not establish that taking a robotaxi is safer than taking public transit.** Those are different comparisons, with different exposure measures and consequences.
>
> ## What the Waymo studies show
>
> “Rider-only” means operation without a human safety driver behind the wheel—not necessarily that a passenger is aboard throughout every mile. The strongest crash study discussed here examined **56.7 million rider-only miles through January 2025**, across Phoenix, San Francisco, Los Angeles and Austin. Compared with human benchmarks, it found these aggregate reductions in crash involvement per vehicle-mile:
>
> | Crash outcome | Estimated reduction | 95% confidence interval |
> |---|---:|---:|
> | Any injury reported | 79% | 71–85% |
> | Airbag deployment | 81% | 69–90% |
> | Suspected serious injury or worse | 85% | 39–99% |
>
> These outcomes include injuries to **any party involved**, not just Waymo occupants; airbag deployment likewise includes other involved vehicles. The serious-injury-or-worse result is encouraging but rests on only two Waymo crashes, explaining its much wider uncertainty interval. It should not be presented as a precise estimate of fatality risk alone. [1]
>
> The findings are consistent with earlier work. At 7.14 million rider-only miles, a study found **55% fewer police-reported crash involvements**—2.1 versus 4.68 per million miles—although comparisons encompassing all property damage or injury were inconclusive because of reporting-threshold and benchmark difficulties. [2]
>
> Insurance evidence points in the same direction, using a different outcome. An earlier published study found zero bodily-injury liability claims over 3.87 million rider-only miles and 76% fewer property-damage liability claims than its human baseline. Zero observed claims does not mean zero underlying risk. [3] A larger, 25.3-million-mile claims analysis reported on Waymo’s research site found 88% fewer property-damage claims and 92% fewer bodily-injury claims versus its overall human benchmark; the corresponding reductions versus a newer-vehicle benchmark were 86% and 90%. These are **liability-claim frequencies**, not counts of all crashes or all injuries. [4]
>
> ## How strong is that conclusion?
>
> These are meaningful real-world results, not merely demonstrations or simulations. But they are **observational benchmark comparisons**, not randomized comparisons of identical trips. The crash research aligns vehicle types, road types and geography, including spatial reweighting to reflect where Waymo actually drives. The 56.7-million-mile analysis concerns surface streets, excluding freeways. Its findings should therefore be applied to the studied operating conditions, not automatically to every road, weather condition or autonomous-driving company. [1][1]
>
> Reporting also matters: human injury crashes are underreported, and the any-injury benchmark uses an adjustment for that; the airbag and serious-injury benchmarks do not. Benchmark uncertainty is not completely captured by the reported confidence intervals. [5] All authors of the 56.7-million-mile study were Waymo employees. That does not negate the findings, but it makes independent replication valuable. [1]
>
> ## Why this does not settle robotaxis versus public transit
>
> **A lower crash rate than human-driven cars is not a demonstrated advantage over buses or trains.** Three distinctions matter:
>
> - **Vehicle-miles versus passenger-miles.** Comparing transport modes requires accounting for how many people they carry and for empty travel to pickups. A low crash rate per robotaxi vehicle-mile does not by itself establish a low rate per passenger-mile relative to transit. [6]
> - **Passenger safety versus total road harm.** Waymo’s headline injury-crash measure includes all involved road users. A transit comparison must consistently distinguish passenger injuries, injuries to others, crash involvement and injury counts. [1][7]
> - **Individual choice versus systemwide impact.** Safety benefits depend on what a robotaxi trip replaces. Replacing a human-driven car trip and replacing a transit trip are not equivalent counterfactuals. Estimates of total injuries prevented also depend on ridership, occupancy and additional vehicle travel. [6]
>
> There is affirmative evidence for transit’s safety benefits, though not a direct Waymo comparison. A study of ten Montreal urban bus routes found car occupant injury rates **3.7 times** bus occupant rates per passenger-distance; pedestrian and cyclist injury rates associated with car travel were also higher. Those findings are route-specific and cannot simply be combined with Waymo’s percentage reductions to rank the two modes. [7]
>
> A separate BART–Waymo analysis estimated lower injury-event rates for BART, but it constructed an approximate severity match and used occupancy, empty-mileage and other assumptions. It is useful as an illustration of the comparison problem, not a definitive head-to-head safety estimate. [6]
>
> **Bottom line:** Safety is a defensible reason to favor Waymo over a human-driven car in comparable studied conditions. The published evidence does **not** justify a general safety recommendation to replace public-transit trips with robotaxis. An individual transit-versus-robotaxi decision requires a more directly comparable, trip-specific assessment than the headline Waymo reductions provide.

- **[1] [Full article: Comparison of Waymo Rider-Only crash rates by crash type to human benchmarks at 56.7 million miles](https://www.tandfonline.com/doi/full/10.1080/15389588.2025.2499887)** (E8; exact saved material: E8, E10, E22). Preview: Provides the 56.7-million-mile crash results, confidence intervals, outcome definitions, rare-event limitations and author affiliations.
- **[2] [Full article: Comparison of Waymo rider-only crash data to human benchmarks at 7.1 million miles](https://www.tandfonline.com/doi/full/10.1080/15389588.2024.2380786)** (E1; exact saved material: E1). Preview: Provides the earlier police-reported crash comparison and explains why broader property-damage comparisons were inconclusive.
- **[3] [Comparative safety performance of autonomous- and human drivers: A real-world case study of the Waymo Driver - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11305169/)** (E2; exact saved material: E2, E29). Preview: Supplies the earlier rider-only insurance-claims results, which measure a different safety outcome from crash involvement.
- **[4] [Do Autonomous Vehicles Outperform Latest-Generation Human-Driven Vehicles? A Comparison to Waymo's Auto Liability Insurance Claims at 25 Million Miles](https://waymo.com/research/do-autonomous-vehicles-outperform-latest-generation-human-driven-vehicles-25-million-miles/)** (E16; exact saved material: E28, E16). Preview: Reports the expanded 25.3-million-mile liability-claims analysis and comparisons with both overall and newer-vehicle human benchmarks.
- **[5] [Safety Impact](https://waymo.com/safety/impact/)** (E4; exact saved material: E4). Preview: Explains reporting differences, human underreporting adjustments and uncertainty in the benchmark comparisons.
- **[6] [Are Self-Driving Cars Safer than Public Transit?](https://thenextmile.substack.com/p/are-self-driving-cars-safer-than)** (E12; exact saved material: E12). Preview: Develops a passenger-mile-based Waymo–BART comparison and states the assumptions behind its severity matching and estimated safety impact.
- **[7] [Traveling by Bus Instead of Car on Urban Major Roads - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5906382/)** (E15; exact saved material: E15). Preview: Provides route-specific evidence comparing bus and car injury rates for occupants, pedestrians and cyclists per passenger-distance.

### Nobel factual control

Question: Who received the 1921 Nobel Prize in Physics, and what achievement did the official prize citation recognize?

> **Albert Einstein** received the 1921 Nobel Prize in Physics. The official citation recognized him “for his services to Theoretical Physics, and especially for his discovery of the law of the photoelectric effect.” [1]

- **[1] [The Nobel Prize in Physics 1921 - NobelPrize.org](https://www.nobelprize.org/prizes/physics/1921/summary/)** (E1; exact saved material: E1). Preview: The official Nobel Prize page identifies Einstein as the laureate and provides the prize citation.

## Fidelity and editorial assessment

An independent agent reviewed the new answers and every preview against exact
public originals supplied initially or by delegated Research; no outside sources
were checked. Every cited material matched actual delivery byte for byte.
In Waymo, E22/E28/E16/E29 arrived through delegated delivery rather than the
initial packet. The first source's three saved excerpts and the two-version
insurance sources legitimately share one description per identity. All seven
previews are short, source-specific and faithful; none claims full-publication
inspection from an extractive highlight. The Nobel preview accurately identifies
what the official record contributes. The unable draw correctly leaves metadata
empty rather than attaching unrelated same-name material.

The compact control demonstrates restrained communication: it answers recipient
and achievement directly, and does not narrate the irrelevant ceremony-year
detail present in the source. The initial identity gap is consequential and is
stated without inventing experience or office history. The comparison preserves
rider-only exposure, geography, crash-versus-claim definitions, vehicle-versus-
passenger miles, injuries to all parties versus occupants, and mode-substitution
effects. Those distinctions materially affect the conclusion.

Restraint remains mixed in that comparison. The zero-observed-claims warning,
generic independent-replication commentary, warning about other autonomous-driving
companies, and repeated transit nonconclusion could be more economical. Author
affiliation may inform evidence assessment, but the following boilerplate adds
little. The generated answer also has an adjacent repeated `[1][1]` reference;
both resolve correctly and reuse one preview. These are retained observations,
not silently edited examples or evidence of general prompt success.

## Browser verification and screenshots

The real application was reviewed at 1440×1000 desktop, 390×844 touch/mobile and
320×720 narrow mobile using synthetic public fixtures. No JavaScript errors or
horizontal overflow were observed. The preview measured 360×255.6px desktop,
360×276.1px at 390px and 296×319.3px at 320px. Three browser regression tests cover
hover persistence, direct publication navigation, keyboard focus/actions/Escape,
touch tap, saved excerpt expansion and narrow-width layout.

After actual product completion, all eight generated descriptions, original URLs
and exact saved material were checked again on both desktop and mobile after
durable reopening. Original-link navigation was fulfilled locally by the browser
test, proving the destination without an independent public-source request.
The publication URL itself is never changed. Historical/PDF paths additionally
have focused offline regression coverage.

Screenshots, all real UI with public or synthetic fixture content:

- [Synthetic desktop preview](C:/tmp/citation-previews-editorial-01/screenshots/desktop-preview.png)
- [Synthetic mobile preview](C:/tmp/citation-previews-editorial-01/screenshots/mobile-preview.png)
- [320px mobile preview](C:/tmp/citation-previews-editorial-01/screenshots/mobile-320-preview.png)
- [Mobile exact saved excerpt](C:/tmp/citation-previews-editorial-01/screenshots/mobile-saved-excerpt.png)
- [Actual Waymo desktop preview](C:/tmp/citation-previews-editorial-01/screenshots/product-2-desktop-preview.png)
- [Actual Nobel mobile preview](C:/tmp/citation-previews-editorial-01/screenshots/product-3-mobile-preview.png)

## Offline verification

The applicable complete suite passed: **1,071 passed**, including the three
optional real-Edge browser tests. Ruff, Python compilation, Git whitespace checks
and all six configured hooks passed. Focused tests cover validated identity
matching, combined/repeated citations, multiple versions and excerpts, invalid or
uncited aliases, missing/malformed metadata, strict primary validation, native API
and personal-plan delegation/citation correction, source-free/partial/unable
results, PDF custody, historical decode/re-encode, durable reopening, escaping,
exact URLs and secondary saved material.

Sandbox TEMP permissions initially prevented storage fixtures; task-owned
TEMP/TMP and unique pytest directories resolved that without runtime changes.
Headless Edge required the ordinary user execution context outside the sandbox.
One old assertion comparing an exact semantic-only model dump was updated to
exclude optional presentation metadata. The final full run passed with no skips.
This is a focused extension of existing tests, with no new test framework.

## Evidence custody, changed files and handoff

Exact new public-source cases were preserved as development candidates, not gold,
under ignored `local-evals/candidates/citation-previews-editorial-01-*` with hashes,
questions, supplied originals, answers, previews, configuration and safe counters.
No hidden reasoning, credentials, private sessions, raw provider envelopes or
database copies enter that corpus. Prior cases/gold remain unchanged. Original
run databases and observers remain under
`C:\tmp\citation-previews-editorial-01\run-{1,2,3}`; no evidence cleanup occurred.
The lookup identity boundary and comparison's editorial blemishes are preserved.

Exact changed files relative to verified production:

```text
CURRENT.md
PRODUCT.md
README.md
docs/architecture/RESEARCH.md
docs/operator/CITATION_PREVIEWS_EDITORIAL_01.md
scryraven/presentation.py
scryraven/reading_room.py
scryraven/research.py
scryraven/results.py
scryraven/session_store.py
scryraven/static/reading_room.css
scryraven/static/reading_room.js
scryraven/templates/reading_room.html
tests/reading_room_samples.py
tests/test_answer_evidence_layout.py
tests/test_answer_finalization.py
tests/test_answer_presentation.py
tests/test_citation_descriptions.py
tests/test_citation_preview_browser.py
tests/test_reading_room.py
```

`CURRENT.md` describes the local experiment and actual evidence; it does not
declare deployment. Local `main` and `origin/main` remain at the verified production
commit. No push, PR creation, merge, rebase, branch deletion, destructive reset or
unrelated cleanup was performed. Review the local feature and especially whether
the remaining comparison prose meets the intended editorial standard. This is a
recommendation for review; no publication or successor phase is implied.
