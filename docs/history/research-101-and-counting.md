# ScryRaven Research 101 and Counting

## Building an evidence-grounded research assistant—and learning what research actually demands

**Project:** ScryRaven · **Creator and product owner:** Aidan (`aidan600`)
**Retrospective edition:** October 1, 2026 · **Repository snapshot:** `8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6`
**Coverage:** selected architectural history from the May 27 public snapshot through PR #665, with detailed attention to the recent Research-effectiveness investigations.

> **Historical reference, not operating instructions.** This document describes what was built, tested, learned, rejected, and still uncertain at the stated snapshot. It does not authorize a new experiment, prescribe a roadmap, or supersede `PRODUCT.md`, `CURRENT.md`, `AGENTS.md`, or the current architecture documentation. Historical models, limits, prompts, and provider choices are not recommendations for future execution.

*Prepared with AI-assisted repository research, source review, and writing for the project owner’s review. The evidence base includes pinned repository documents and PRs, supplied local experiment reports, and separately identified public industry sources. The source register distinguishes these levels of access. This is selective technical history, not a claim to have audited every commit or independently reproduced every experiment.*

---

<a id="executive-summary"></a>
## The achievement, before the postmortem

ScryRaven’s most important achievement is a working answer to a deceptively demanding product question:

> Can a research assistant investigate a question, change its approach because of what it reads, and produce an answer whose factual support remains inspectable?

By this edition, the project had demonstrated that behavior across several kinds of questions. It could answer authoritative lookups; combine related facts into a coherent explanation; discover an entity and then search for a specification it could not have requested precisely before that discovery; reopen a saved conversation and reuse actual source material; perform arithmetic without treating the calculation as new empirical evidence; and produce useful partial answers rather than inventing a missing common basis. The ordinary CLI and browser Reading Room shared the same underlying research/session application. These were bounded demonstrations, not a universal reliability claim. [R09], [R10]

One particularly revealing success concerned a NASA/GE hybrid-electric demonstration. The system first had to establish which base engine had been modified. Only after reading that evidence could it ask for the applicable GE-published takeoff-thrust range. The recorded successful trajectory made that transition: the first queries did not name Passport, the acquired material established the identity, and later acquisition found the specification. That is more meaningful than a correct answer produced from a lucky first search containing everything. [R09]

Another success was less theatrical but just as important. A reopened BIPM conversation could answer a follow-up by reading previously acquired material, with no new external acquisition, while leaving the earlier answer and its citations intact. The product had learned to reuse evidence rather than reuse its own assertions. [R09]

The system’s distinctive boundary became clear: **a model’s account of a source is not the source**. Research’s working notes guide investigation but do not become factual authority. The final Answer role reads selected actual material afresh. Citations resolve to acquired text, including preserved versions and exact views. Mechanical checks verify custody and literal membership; they do not pretend to prove every semantic claim. [R11], [R19]

This capability came with a difficult tail. Some questions finished quickly. Others provoked repeated search, unnecessary rereading, lost qualifications, and enough sequential model calls to make the product feel slow. Sources could remain safely stored while vanishing from the material selected for the answer. A model could explicitly recognize a comparison problem and still keep searching without a convincing next step. Stronger models repaired individual decisions without establishing a better whole-run bargain. [L06], [L07], [L12]

The investigation therefore became less about making an impressive agent diagram and more about locating the expensive mistakes. Was a page never discovered? Was it found but not fetched? Was its important section outside the model’s current attention? Did the model read and then discard it? Did the final answer omit a qualification that had actually reached it? Those are different failures with different remedies.

Several practical improvements survived: a simpler two-owner semantic architecture; exact recoverable source custody; clearer source-operation behavior; selected follow-up evidence supplied earlier; lossless catalog tables; provider-native Dynamic Highlights; configurable model roles; and natural-language evidence objectives for generic Exa Search. Other attractive ideas did not earn adoption: model-facing novelty histories, universal first-search orientation, uniform excerpt shrinkage, a displacement warning, a cheap “parking brake” reviewer, and an early drop-in Deep-search replacement. [R09], [R12], [R13], [R17], [R18], [L01], [L13], [L15]

The portfolio value is not a claim that a solo project outperformed a major research platform. It is the construction of a capable, inspectable research product **and a body of evidence explaining its limits**. The project learned to distinguish interface improvements from intelligence improvements, local successes from trajectory reliability, cheap requests from cheap completed work, and a failed experiment from a failed product thesis.

The most durable lesson is this:

> **A research assistant is not primarily a text generator attached to search. It is a sequence of decisions about what evidence is needed, what has actually been obtained, what it means, what deserves another operation, and what must survive into the answer.**

---

## Reading routes

For the product story, read **1–4**. For the practical research failures and experiments, read **5–11**. For industry comparisons and small-budget development, read **12–14**. For the dated endpoint and reusable lessons, read **15–16**. The [experiment library](#experiment-library) and [source register](#source-register) make the document usable as reference rather than only as a narrative.

## Contents

1. [What was working at the snapshot](#working)
2. [The architectural journey](#journey)
3. [The product boundary that survived](#boundary)
4. [What a research turn actually costs](#cost)
5. [Four problems that looked like search failures](#cases)
6. [Making context smaller without making research worse](#context)
7. [Continuity, retention, and stopping](#control)
8. [What stronger models did—and did not—buy](#models)
9. [The web is not one readable database](#materialization)
10. [Buying managed research without surrendering evidence](#managed)
11. [Learning to use Exa on its own terms](#query-language)
12. [What industry had built, and what transferred](#industry)
13. [What small-sample engineering can legitimately establish](#evaluation)
14. [The test harness is part of the experiment](#harness)
15. [State of the project at the time of writing](#snapshot)
16. [What the work demonstrates](#takeaways)
17. [Experiment library](#experiment-library)
18. [Source register and evidence-access notes](#source-register)
19. [Glossary](#glossary)

<a id="working"></a>
## 1. What was working at the snapshot

The clearest way to describe the product is to begin with operations it had actually exercised, not with model names or the number of tests in the repository.

| Capability | Demonstrated behavior | Important boundary |
|---|---|---|
| Authoritative factual lookup | BIPM prefixes answered from acquired resolution/announcement material; later formulation work preserved a one-Search lookup. | A few successful lookups are not a reliability rate. |
| Multi-need factual synthesis | The promoted path answered a JWST question covering partners, launch, orbit, mirror, and wavelengths. | Several requested facts arriving together does not prove dependent research. |
| Evidence-dependent acquisition | Passport’s identity became known from sources, then changed the next searches toward its thrust specification. | The dependency was demonstrated in particular trajectories, not guaranteed on every run. |
| Follow-up research | A reopened BIPM session used retained actual material without external acquisition. | Prior assistant prose remained discourse context, not support. |
| Missing-premise restraint | Anker/FAA work distinguished battery capacity units and refused to derive watt-hours from milliamp-hours alone without voltage. | The initial confirmation was incomplete on a specific source obligation; that record was preserved. |
| Qualified, open-world synthesis | Bounded Level-7 diagnostics distinguished sampled discussion from stronger representative-survey support. | Community-source access blocked some live cases; population-wide reliability was not established. |
| Dynamic task handling | The recorded Level-8 campaign exercised changing scope, premise revision, multi-turn reasoning, and conditional calculations in seven of eight families. | Individual imperfections remained; one family was operationally unassessable. |
| Inspectable source use | Exact selected material, versions, local views, literal readings, and historical citations persisted through sessions. | Custody and quotation membership do not prove entailment or completeness. |

These distinctions are grounded in the mainline promotion record and the snapshot’s current-truth account. They deliberately separate live demonstrations, frozen diagnostics, and mechanical checks. [R09], [R10], [R11]

### A meaningful research product, not just a loop demo

The product included persistent conversations, reopened follow-ups, revision-checked storage, historical citation inspection, and a browser Reading Room. Those features matter to research because the meaning of an answer depends on which material was available at the time. Later acquisition must not silently change what an earlier citation opens. A useful partial answer must survive reopening just as a supported answer does. [R09], [R11]

The same care made failures more informative. If an answer omitted an aircraft-variant qualification, the project could distinguish whether the qualification was missing from retrieval, outside current attention, absent from Answer selection, or lost in final composition. That did not automatically fix the error, but it prevented a vague diagnosis such as “the model hallucinated” from obscuring the relevant boundary.

### Success without pretending the product was finished

“Capable” and “reliable” are different claims. The project had capability witnesses across a meaningful variety of research operations. It did not have a large representative held-out evaluation establishing their frequency. It also had explicit negative cases.

A fair description is therefore stronger than “a toy that sometimes works” and narrower than “a solved general research agent”: **an end-to-end research application with demonstrated adaptive behavior, unusually explicit evidence handling, and a documented reliability frontier**. That is this retrospective’s assessment of the combined record, not a leaderboard result.

<a id="journey"></a>
## 2. The architectural journey: from formal control to accountable iteration

### 2.1 The earliest verified public state was already a substantial prototype

The May 27, 2026 commit named **Initial public snapshot** describes a cleaned public release of an earlier private prototype. That establishes the beginning of the public history reviewed here—not the date the private project began.

Its README describes a backend pipeline that classified intent, generated searches, retrieved and chunked sources, ranked evidence, invoked analysis/audit passes according to mode, rendered cited reports, and saved research threads. A Streamlit interface sat above a backend entrypoint in `core/pipeline_orchestrator.py`. The project already cared about source obligations and insufficient evidence. It was not initially just a thin call to a hosted answer API. [R01]

The early ambition was understandable. Different questions appeared to require different treatment; claims needed appropriate sources; follow-ups needed continuity; numerical analysis needed to remain source-bound; and a final writer should not fabricate support. The difficulty was deciding how much of this to encode in software contracts and how much to entrust to semantic judgment.

### 2.2 The formal-control era encoded increasingly detailed authority

By July, the repository contained graph admission, component recovery, scheduling leases, and several role-specific handoffs. These were not merely metaphorical “agents.” The contracts tracked which component, source obligation, graph revision, request, and authority state permitted a result to be used.

PR #472 introduced deterministic RunKernel admission over component graphs and synthesis-validation references. Its own description explicitly distinguished that contract from executing or scheduling the graph. PR #480 extended the path with one bounded missing-component recovery, a versioned AnswerContract amendment, source-lineage binding, graph revision, and fresh resynthesis. PR #483 installed a grant-first scheduler with exact leases, spend commitment, stale-work rejection, and completion rules. Runtime parallelism remained disabled in that phase. [R02], [R03], [R04]

There were real engineering problems behind the formality. A late result should not be accepted against an obsolete task. A recovered source should satisfy the actual missing obligation, not another obligation with a similar label. A caller should not be able to manufacture canonical authority by submitting a plausible reference mapping. The PRs document focused corrections to precisely such defects.

But the validation claims were often about **structural integrity**: a result had the right lineage, an invalid transition was rejected, or a scheduler could not complete with an active lease. The cited graph PRs did not establish broad live research quality. A system can be internally consistent about the provenance of a weak interpretation.

The retrospective lesson is not “graphs are bad.” It is that detailed machinery can expand the amount of state that must be correct without resolving the semantic decisions that motivated it. The reviewed history supports an interpretation of growing coupling and verification burden; it is not a controlled experiment proving that fewer lines of code cause better reasoning.

### 2.3 The reset preserved history without preserving the implementation

PR #623 retired the active v1 application and control-plane estate, keeping a small foundation and selected neutral transport donors. It preserved the final v1 implementation in a historical tag rather than keeping an executable fallback inside the new product tree. The reset itself intentionally contained no working Research/Analyst/Author pipeline or product entrypoint. [R05]

This was a consequential distinction: **preserving what was learned did not require preserving every runtime abstraction**.

PR #624 then added a walking skeleton: Research discovered and fetched material, Analyst assessed it and could request follow-up, and Author wrote from selected support. Live chess-promotion and bowling-ball-limit examples worked. The phase explicitly did not claim multi-component competence. Calling this version “incapable” would erase its real narrow successes; calling it the completed product would erase its limits. [R06]

### 2.4 A smaller system still had to learn how to investigate

The Investigator lineage tested a more concentrated controller. It produced useful factual explanations and comparisons, but repeatedly failed to change unproductive routes. The behavioral record includes a director-identity question that generated fifteen searches while an acquired linked role document went unused, and a future visitor-total question that continued extensively despite recognizing the temporal problem. Two interventions clarified evidence-directed action and tool prerequisites. The candidate still did not earn its intended architectural claim. [R07]

The early V2 implementation similarly proved valuable mechanics without proving the full research capability. Ten submissions exercised actual sessions, local source views, citations, and partial answers. Yet rule scope was broadened incorrectly, qualifications were omitted despite arriving in context, reception was overstated from a limited sample, and departure chronology was lost before further research on an old candidate. Removing generated cautions from the final handoff and requiring literal source readings improved the boundary without making semantic fidelity automatic. [R08]

These were not wasted versions. They separated several questions that had been entangled: can the product acquire and retain text; can it expose the requested region; can the model use it correctly; and can the writer preserve what matters? The answers were different.

### 2.5 The successful core was two semantic owners, not zero structure

The later accepted lineage promoted one Research owner and one fresh Evidence-first Answer owner. It removed the old Analyst checkpoint and separate Author handoff from ordinary execution. It retained exact source custody, mechanical tools, citations, sessions, and application surfaces.

The capability ladder mattered. A correct answer obtained from a first batch that already contained the answer was not counted as a demonstrated dependent search. The Passport trajectory supplied a stronger witness: acquired identity changed the next information request. Reopened BIPM reuse and the Anker missing-premise case tested different promises. [R09]

The resulting system was neither the old formal graph system nor an unconstrained chat loop. It assigned semantic meaning to models and identity, exact material, transport, budgets, and persistence to code. That allocation became the basis for the subsequent efficiency investigation.

### 2.6 A timeline of transitions, not a victory march

| Period / anchor | Architectural emphasis | What the record supports |
|---|---|---|
| May 27 public snapshot | Mode-dependent grounded research pipeline | Existing private prototype exposed publicly; retrieval, ranking, analysis, audits, and follow-ups described. |
| July graph/recovery/scheduler work | Explicit component and authority control | Substantial mechanical contracts and tests; specific lineage defects repaired; broad live efficacy not established by these PRs. |
| September reset, PRs #623–624 | Small foundation, then narrow working product | Earlier implementation retired; simple factual product path demonstrated. |
| Investigator and initial V2 investigations | Adaptive semantic control with preserved evidence | Real successes alongside repeated interpretation, retention, and stopping failures. |
| September 20 accepted lineage | Research → mechanical acquisition → fresh Answer | Counted evidence-dependent transitions and ordinary compatibility demonstrated. |
| Late September–October 1 | Context, acquisition, model economics, stopping, provider calibration | Several mechanisms consumed, several rejected, and narrower claims about what each experiment establishes. |

This is selective history. The repository contains more transitions than this table, and changed models, prompts, providers, limits, and tasks prevent a simple before/after causal claim across the entire project.

<a id="boundary"></a>
## 3. The product boundary that survived simplification

ScryRaven’s most stable architectural idea was not a particular model or orchestration graph. It was the separation between **information received**, **interpretation generated**, and **claims delivered**.

```text
Question and conversational intent
                  |
                  v
       Research: interpret and choose
                  |
                  v
 Search / lexical Search / Read / Find
                  |
                  v
     Immutable source custody + views
                  |
                  v
      Research: reassess and select
                  |
                  v
    Fresh Answer: read actual Evidence
                  |
                  v
 Literal-reading / citation checks -> saved answer
```

At this snapshot, ordinary Research had no separate Planner, Scout, semantic verifier, standing critic, or specialist swarm. “Research” and “Answer” were semantic roles whose concrete models came from configuration. Code could move and validate data without pretending to decide whether two aircraft cost estimates were comparable. [R11], [R17]

### Three forms of memory with different authority

**The acquired library** retained source material and versions. **Current attention** was the subset supplied to the next model call. **Generated working understanding** recorded the controller’s interpretation and unresolved needs. They served different purposes.

A model could shelve an item from attention without deleting it. It could later inspect it with local Read or Find. Conversely, an item in the catalog was not necessarily material the model had read. The system therefore distinguished addressability, exposure, interpretation, and final selection. [R11], [L07], [L08]

This design allowed aggressive attention management without destructive factual memory. It also exposed a weakness: recoverability does not make the model recover the right thing. A catalog can perfectly identify a source whose relevance the controller no longer appreciates.

### Literal evidence is not necessarily complete evidence

A provider-selected excerpt can be useful factual support. Re-fetching the page is not automatically necessary if the received passage establishes the relevant claim and qualifications. But an excerpt is not a guarantee that no omitted exception, table heading, date, or variant matters.

The same applies to fetched bodies. “Full” means the readable representation the provider returned, not a guarantee of perfect extraction from the original publication. Large parents may be exposed in bounded exact views. Exactness solves a custody problem; it does not solve every completeness problem. [R11], [R19]

### The clean Answer boundary

Research did not send a factual verdict for the writer to decorate. It selected actual material. Answer received that material, the question, and appropriate non-evidentiary conversation context, then made its own support judgment.

The literal-reading contract required passages to occur in supplied material. Citation resolution bound references to selected sources and exact views. These checks could reject an invented quotation or an unselected reference. They could not mechanically prove that a passage’s scope supported the sentence attached to it. [R11], [R15]

This restraint is part of the product’s integrity. **“Our citation validator passed” is not another spelling of “our answer is true.”**

<a id="cost"></a>
## 4. What a research turn actually costs

The expensive unit was often not one retrieval request. It was another model decision over an accumulated working set, followed by another round of acquisition and reassessment.

A useful accounting model is:

```text
Completed-turn cost = all model input + all model output
                    + external acquisition charges
                    + operational overhead

Completed-turn latency = serial model time + serial tool time
                       + coordination / local processing
                       - overlap actually achieved
```

The terms should be measured, not inferred from the number of semantic role labels. An Answer calculator continuation can involve another physical model request while remaining one semantic Answer attempt. A provider’s “one research request” can contain substantial internal orchestration. Those are different accounting boundaries. [R11]

### Cumulative input is not one giant context window

In the controller comparison, Luna consumed 272,204 Research input tokens across eleven submissions; Sol consumed 237,440 across eight. These were sums across calls. The corresponding average input sizes were approximately 24,746 and 29,680 tokens per submission—not single 250,000-token prompts. Reported cached input represented only about 7.5% and 6.2% of those totals. [L12]

Each Research call reconstructed current state rather than replaying every earlier intra-turn tool exchange. The 128,000-character allowance applied to current source-body attention, not the entire request. Instructions, catalog, working understanding, conversation, and operational metadata added more input. Pending material could displace selected material temporarily; later decisions could drop it semantically. [R11], [L08]

Therefore, both of the following were true:

- The system already kept much of the source corpus outside model attention.
- It could still repeatedly pay to present a substantial working set.

### Latency moved between layers

A ten-turn latency flight attributed roughly 65% of elapsed time to Research models, 25.4% to Answer, and 9.5% to external I/O. Other cases had much heavier fetch delays. In the latest query-formulation campaign, St. Dorothy’s failed Reads and repeated acquisition consumed considerable time; the MD-80 Answer recovery alone later took 95.953 seconds. These are different campaigns and must not be blended into one universal latency profile. [R10], [R18]

That is why “faster search,” “fewer searches,” “fewer Research calls,” and “faster final answer” cannot be treated interchangeably. Cutting a Research call helps, but a lengthy high-reasoning Answer can still dominate the user’s wait. Increasing a service tier’s speed also does not guarantee a faster end-to-end run if the model takes a different path.

### Unit economics can reverse a model-ranking conclusion

A model may be cheaper per token and expensive per completed task because it repeats work. A stronger model may reduce steps but remain more expensive because it does not reduce enough input or output. A reviewer can be cheap relative to a premium actor and expensive relative to Luna. A lower-latency provider return may omit material that requires later recovery.

These are not reasons to stop measuring. They are reasons to measure the **whole completed operation**, preserve missing counters as unknown, and keep provider tariff estimates separate from actual billing.

<a id="cases"></a>
## 5. Four problems that looked like search failures

### 5.1 Passport: finding the right entity before asking the right question

The Passport question was valuable because it tested a real dependency. NASA and GE had multiple electrification programs. Material about a different engine could be authoritative, current, and still inapplicable to the requested demonstration.

Successful trajectories established the relevant modified base engine, then sought that engine’s GE-published thrust specification. Unsuccessful or expensive trajectories followed an adjacent program and pursued its values. Lower reasoning effort was not consistently cheaper: in one preserved comparison, the medium-effort path spent longer on the wrong program and returned a partial answer, while high effort obtained the controlling range. [R09], [R10]

This case also showed how to evaluate an adaptive system fairly. If the first search already returns both identity and specification, the answer can be correct without exercising dependency management. That is a product success, but weaker evidence for the particular capability being tested.

Later, objective-style Exa Deep returned both the relationship and datasheet in one provider call. That was genuinely useful acquisition evidence. It did not prove that the full ScryRaven controller would always recognize the pair, select it correctly, or stop. [L16]

**Lesson:** relevance to the topic is not the same as relevance to the relationship the question requires. A specific dependency witness is more informative than a generic “multi-hop” label.

### 5.2 St. Dorothy’s: a correct biography is not an appointment

The director question repeatedly crossed three separate evidentiary bridges: identify the selected person; establish the appointment/transition relationship; and establish that person’s relevant qualifications.

Search could return a recruitment profile, an interim director, an older staff page, or a compelling biography. None alone proved the current selection. A biography for a promising candidate was useful discovery, but it could not silently establish that the organization had appointed that candidate.

This task produced failures at different layers over time. An early V2 run exposed departure chronology and then lost it while continuing research on an older candidate. A later ordinary Serper route found an official social post that LinkUp successfully materialized, supporting the selection. A Dynamic experiment acquired transition evidence and supplied it to Answer, yet the final prose omitted that chronology. In the latest formulation campaign, the necessary post Reads failed, so the honest final answer left the appointment unconfirmed. [R08], [R10], [L05], [L07], [R18]

Those outcomes should not be collapsed into one repeating “Dorothy failure.” The earliest case concerned interpretation and retention. Another concerned final-answer coverage. The latest included a concrete source-access failure. The same user question exposed different defects as the architecture and source returns changed.

Natural-language Exa Deep eventually improved the candidate-qualification frontier, including primary material about earlier experience. It still did not establish the appointment bridge. That deserved partial discovery credit, not a supported answer. [L16]

**Lesson:** the controlling fact is often a connection, not an isolated entity attribute. Research must preserve the difference between a lead, a verified relationship, and a useful but conditional biography.

### 5.3 MD-80 versus 777-300: arithmetic was the easy part

The aircraft question asked for a difference in average cost per passenger-mile. It sounded precise but left difficult measurement work underneath: aircraft variants, operator populations, periods, direct versus allocated total costs, modeled versus observed values, and available seats versus occupied passenger distance.

For a single aligned sample and cost definition, the algebra is straightforward:

```text
Cost per revenue passenger-mile
    = cost per available seat-mile / load factor
```

But that expression cannot manufacture an absent type-specific load factor, align different years, equate fuel consumption with total operating cost, or turn a 777-200 figure into a 777-300 figure. Nor is an unweighted average of airline ratios automatically the ratio of total cost to total passenger distance. These distinctions were explicitly reconstructed in the forensic review. [L06]

Several ScryRaven runs reached a useful qualified partial answer early. That did not prove all promising acquisition was exhausted. The decisive counterexample was a dissertation already in local custody. Its chapter described a common empirical dataset and pointed to Appendix B, which included MD-83 and B777-300 rows. Research failed to inspect the relevant appendix. An offline test later used existing scoped Find and local Read operations to expose it without new external acquisition. [L06], [L07]

The appendix was a better common-data lead, not a magically completed answer. MD-83 does not automatically stand for the entire MD-80 family; direct costs are not all costs; descriptive means are not necessarily the required weighted passenger-mile measure. The discovery corrected the claim that the question had no remaining research opportunity without licensing an unsupported scalar.

The case was therefore excellent for diagnosis and hazardous as a single promotion benchmark. A run could be epistemically honest yet inefficient. Another could be fast and numerically confident but compare incompatible quantities. A third could discover better data and still fail to use it. “Did it give the number?” was too crude; “did it refuse?” was also too crude.

The project’s evaluation matured by separating comparability, consequential lead pursuit, retention, useful partial synthesis, and stopping economy. The question did not become invalid. Its role changed from universal referendum on retrieval quality to a deliberately difficult stress case.

**Lesson:** unestablished is not impossible, and refusing unsupported arithmetic is a capability—not an excuse to ignore a concrete next source action.

### 5.4 Reception, commercial success, and sufficient depth

The preserved investigations also included questions whose answers were not single numerical facts. Shoresy commercial success initially drew on launch performance and adjacent commercial indicators; a more targeted route found sustained audience/ranking and ticket-sale evidence. A Wayne/Shoresy comparison, by contrast, had substantial support for the requested developed analysis before further broad character searches continued. [L01]

These cases illustrate opposing errors. An agent can stop after finding topical proxies that do not complete the user’s requested operation. It can also keep searching after the requested depth is supportable, without identifying a consequential missing capability.

France diesel geography added a third possibility: an intermediate Answer introduced an exact-date need the user had not requested, and Research adopted it. Over-research did not necessarily originate in the first Research stopping decision. Applicability to the requested situation—not mechanically finding the newest date—was the relevant standard. [L01]

**Lesson:** useful stopping depends on the requested intellectual operation. A product cannot reduce the problem to a source count, a confidence word, or a universal “stop sooner” instruction.

<a id="context"></a>
## 6. Making context smaller without making research worse

### 6.1 Uniform shrinkage delivered fewer characters and more work

The Search Excerpt Density experiment reduced the per-result highlight allowance from 4,000 to 2,000 characters. Its provider screen confirmed mechanical leverage: eight calls preserved the paired candidate URLs while reducing delivered highlight characters by about 37.2%.

Across the four paired product cases, Search material fell from 285,251 to 194,076 characters, about 32%. Yet cumulative Research input rose from 194,777 to 255,339 tokens, about 31%. Research calls increased from sixteen to nineteen and external attempts from twenty-two to twenty-five. Wall time happened to fall. Those observations were not interchangeable measures of efficiency. [L02]

The treatment’s difficult aircraft trajectory also omitted useful acquired model evidence before Answer. The record located that failure in Research selection; it did not prove the smaller extraction allowance caused it. The result justified rejecting this tested setting, not declaring every shorter excerpt harmful.

### 6.2 Decomposition replaced an attractive story with accounting

An offline trajectory review examined all eight runs and thirty-five Research calls. Its descriptive attribution associated 58,977 of the additional 60,562 input tokens—97.38%—with changed call counts. In the aircraft pair, calls increased from seven to eleven while average input per call changed by only about 1.2%.

Repeated Evidence and growing catalogs also mattered. Only 13,256 of the 91,175 fewer Search characters survived as reduced cumulative Research Evidence exposure. The rest of the trajectory’s reuse and acquisition substantially offset the initial payload saving. The accounting was informative, but reconstructed field sizes and missing full historical packet bytes limited exact field-level token attribution. [L02]

The practical lesson was not “never optimize packets.” It was **do not buy a smaller packet by accidentally purchasing another cycle over most of the same state**.

### 6.3 Lossless catalog tables were a better kind of intervention

The catalog represented many rows with repeated field names. Converting adjacent equal-key rows into column-labeled tables preserved every row, value, identity, order, and absent-versus-null distinction. No source body had to be summarized or evicted.

Across thirty-five reconstructed states, catalog characters fell 28.75%. Reconstructed packet characters fell 8.98%, or 8.57% when the new explanatory instruction was counted per call. Exact inversion supplied a strong deterministic claim: the representation retained the logical information. [R12], [L03]

The behavioral campaign was less clean. Frozen model input fell, and product pairs had encouraging aggregate economy, but a required aircraft confirmation lost useful evidence before Answer. The formal whole-product disposition remained inconclusive. A later product decision nevertheless adopted the lossless representation in PR #662, explicitly without claiming improved semantic reliability. [R12], [L04]

That decision was not a retroactive rewriting of the experiment. It separated an established representation benefit from an unestablished end-to-end superiority claim. Such distinctions are necessary in practical engineering: not every reversible, understandable improvement needs to become a universal performance theorem.

### 6.4 Dynamic Highlights changed allocation, not just a ceiling

Provider-native Dynamic Highlights addressed a different variable: how excerpt material is allocated across results. The candidate kept ordinary Search while delegating selection to the provider’s extraction mechanism. Generated synthesis still could not become Evidence. Exact returned selections and their discontinuities were preserved. [R13]

The original campaign again remained inconclusive at the whole-product gate. The expensive aircraft trajectory did not establish extraction as the cause of repeated work; a Dorothy omission occurred downstream in Answer after the relevant material arrived. A later architecture decision consumed the acquisition mechanism, and PR #663 integrated it with offline custody checks. [R13], [L05]

The gain was not “Search is now solved.” It was a more appropriate allocation mechanism without another ScryRaven model round trip.

### 6.5 Some useful context wins were straightforward

Earlier work supplied a follow-up with exact material cited by the preceding answer when it fit the existing attention allowance. In two copied-session observations, this reduced Research calls from four to two and eliminated three local Reads; an unrelated question still acquired new material. This was a concrete improvement in starting context rather than generated memory. [R16]

Packet-order changes and removal of an unnecessary `purpose` field also survived bounded checks. They reduced procedural burden without creating another semantic responsibility. Their effect on general latency or judgment was not established. [R10]

Together these results support a differentiated view of compression: **lossless metadata compaction, earlier delivery of relevant exact material, provider passage allocation, destructive eviction, and generated summarization are not one technique**.

<a id="control"></a>
## 7. Continuity, retention, and stopping: why the obvious repairs were hard

### 7.1 New bytes were not evidence of progress

Exa could return fresh highlight records for familiar URLs. A novelty counter therefore measured acquisition movement, not necessarily a new fact or a useful next step.

Two model-facing novelty/history treatments, including query attribution and expected-yield prompting, produced mixed results. The model-facing history was removed; safe numerical diagnostics remained for humans and forensics. A lost draw in one campaign also exposed an evaluation bug: the harness applied a stricter latest-packet reference rule than production’s cumulative within-turn exposure rule. [R14]

The enduring distinction was **code remembers operations; the model judges meaning**. Operational receipts can be valuable without becoming semantic stopping authority.

### 7.2 Better reminders did not demonstrate better judgment

A task–evidence-fit prompt explicitly asked Research to compare the requested operation, what current material established, the consequential gap, and the likely value of another route. Four paired cases—eight model decisions in total—did not show clear improvement.

A separate contract review concluded that the correct states were already expressible in interpretation, established findings, unresolved needs, and last-route assessment. Proposed declarations such as `answerable_now` or gap identifiers might direct attention, but would still have to be filled by the same model. The review did not establish a missing representational capability. [L01]

That does not mean prompts or schemas never matter. The later Exa formulation change did alter observed query behavior. It means a new field or reminder must have a mechanism beyond restating the judgment that is already failing.

### 7.3 Mandatory orientation solved sequencing and imposed a tax

Compact early discovery had a credible idea behind it: show Research a navigation map before allowing it to accumulate large evidence-heavy search packets.

Optional scouts did not reliably achieve that ordering. In one Dorothy treatment, Research spent fifteen Exa searches first and used scouts only after deep acquisition allowance was depleted. A late scout found a useful identity lead, but the useful ordering had already been lost. [L01]

Mechanical first-search orientation forced the map to arrive early. It improved acquisition economy in a Dorothy observation while preserving answer quality. Yet the final adoption screen found real lookup overhead: the Southwest example used more Research calls, provider attempts, visible characters, and input tokens despite a supported answer. Universal orientation was rejected. [L01]

This taught two different lessons at once. Early compact navigation can help ambiguous discovery. A mandatory extra phase can still be the wrong generic architecture. Neither observation erases the other.

### 7.4 Semantic omission and mechanical displacement were different defects

The retention review separated cases where Research simply stopped retaining useful quantities despite ample capacity from a case where pending-first allocation displaced material it had explicitly nominated.

A crucial wrinkle defeated a tempting automatic repair: carrying forward the latest retain intent would not restore the complete historical trajectory, because a later accepted Research decision explicitly omitted the same material. Overriding that would change semantic shelving authority, not merely repair accidental allocation. [L08]

A conditional displacement receipt was therefore tested as a small intervention. It told the model that intended material had not been delivered without changing priorities or suppressing shelving. In the frozen failure screen, the control and both treatments omitted the controlling source. The candidate was rejected. [L09]

Custody remained correct. The model’s effective use of it did not.

### 7.5 The parking brake tested a new role, not a new source

The Research Parking Brake asked a second Luna call to judge one proposed continuation: continue, redirect to one existing operation, or finish acquisition. It saw the same logical Research packet plus the proposed decision. The envisioned hook was eligible once a trajectory had executed three routes, with no pending delivery, and could run at most once.

The six-state frozen screen failed. Both early continuation controls passed, but neither registered finish case stopped and neither registered redirect obligation was met. The explicit Appendix-B source action remained bypassed. One redirect was plausibly useful as a period-alignment check, but it was unexecuted and did not satisfy its preregistered finish criterion. These details limit any claim that every reviewer action was inherently irrational. [L13]

The measured review averaged about 9.3 seconds and $0.00645 under the frozen rates. No product trajectory ran, so avoided calls, saved acquisitions, and actual latency recovery were unmeasured. The candidate did not earn further execution.

The useful negative conclusion is precise: **same-model review with a different prime directive over this packet did not supply the needed intervention judgment**. It does not refute all critics, stronger reviewers, trained stopping policies, or reviews with new external feedback. It does show why an extra semantic box should not be adopted merely because “independent review” sounds reassuring.

### 7.6 Stopping is not a single truth test

Three questions recurred throughout this work:

1. Is the requested definitive answer established?
2. Is another specific acquisition likely to improve the best available answer?
3. Will the final writer receive the consequential material already acquired?

An honest partial answer can be the right completion even when the first answer is no. A concrete acquired appendix can make continuation worthwhile even when many earlier searches were unproductive. And a correct stopping decision can still produce a weak answer if the handoff drops the useful material.

The project did not identify a cheap, generally reliable rule combining these judgments. It did learn why confidence scores, source counts, byte novelty, and elapsed time are inadequate substitutes on their own.

<a id="models"></a>
## 8. What stronger models did—and did not—buy

The controller comparison held the application’s acquisition and evidence rules fixed and compared historical experiment configurations labeled Luna/high/Fast, Sol 6.1/high/Standard, and Gemini 3.8 Flash/high through OpenRouter. These are recorded configuration names, not a current model recommendation. [L12]

### Local competence improved

On five frozen states, Sol corrected the acquired-appendix decision and two retention failures that Luna reproduced. Gemini corrected the two retention failures but not the appendix action. All three stopped on the simple sufficient-evidence control. All three remained only partial on a repeated-route state.

Sol advanced to the fresh product comparison because of its additional source-action improvement. Gemini’s five frozen calls had a median near forty seconds and no equivalent explicit cache implementation; it did not receive a new end-to-end run. The evidence therefore neither established a production Gemini case nor refuted the model generally. [L12]

### The full aircraft trajectory did not repay Sol’s premium

| Measure in the fresh MD-80 comparison | Luna Research | Sol Research |
|---|---:|---:|
| Research calls | 11 | 8 |
| External attempts | 14 | 15 |
| Cumulative Research input | 272,204 tokens | 237,440 tokens |
| Research output, including reasoning | 13,592 tokens | 3,820 tokens |
| Whole-run wall time | 181.359 s | 196.344 s |
| Estimated Research-model cost | $0.064363 | $0.484945 |
| Estimated total model cost, including the common Answer configuration | $0.124322 | $0.597075 |
| Final posture | Partial | Partial |

The cost estimates use that experiment’s frozen tariff assumptions, exclude acquisition-service dollars, and are not invoices. Both arms used the same Answer configuration, but not the same Answer packet or realized usage. [L12]

Sol used fewer Research calls and much less output. It also used slightly more external acquisition, took longer, and cost about 4.8 times as much in total model inference. Both controllers acquired useful MD-80 model material and subsequently omitted it from the terminal Answer packet. Both stopped under mechanical bounds rather than voluntarily proposing Answer. [L12]

### What can and cannot be inferred

It was tempting to conclude that the harness destroyed Sol’s superior judgment. That is a hypothesis, not a causal finding. The frozen states and fresh trajectories were not identical decision sequences; acquisition, context, timing, and choices diverged. One draw per frozen state and one fresh hard question per selected controller cannot locate a universal cause.

The supported conclusion was that capability improved on some isolated decisions while an economically attractive whole-run improvement was not demonstrated. “Use a stronger model everywhere” was not earned. “The cheap model can never do this” was not earned either.

Moving model, reasoning effort, and service tier into role configuration was consequently valuable for a different reason: it made such choices operationally reversible without embedding concrete model policy in business logic. The subsequent per-user settings boundary allowed local changes without a repository amendment. [R17]

<a id="materialization"></a>
## 9. The web is not one readable database

Retrieval quality was only one part of acquisition. Finding the URL did not mean obtaining the relevant article, PDF, or social post. Obtaining a nonempty body did not mean obtaining the right body.

The known-URL bake-off reviewed six URLs across eight configurations: LinkUp Standard and Pro, each with/without JavaScript; Exa Contents; Tavily Basic and Advanced; and Firecrawl. It was a diagnostic set, not a representative market-share-weighted reliability study. Only bounded previews, hashes, metrics, and adjudications survived for that campaign; complete provider-body fidelity could not be reconstructed from them. [L10]

The pattern resisted a simple ranking. Dipp failed across all configurations. Several stronger methods recovered the Telegraph page. LinkUp Pro without JavaScript recovered Le Monde where Standard with JavaScript still returned a loading shell. Yet Pro+JS failed on a USA Today page that simpler configurations could retrieve. No tested method recovered the actual legacy ICAO PDF. Tavily Advanced recovered some Reddit original-post material, not a dependable complete thread. [L10]

Two distinctions mattered especially.

**Transport success was not task success.** A 209-character loading shell could satisfy a nonblank-body check while containing none of the required article. A fallback triggered only by HTTP/transport failure would miss that case.

**More expensive was not monotonically better.** A rescue configuration could fail on an easier control, and more characters could mean additional page furniture rather than additional answer-bearing substance.

A small frozen screen offered a provider-opaque alternate Read rather than asking Luna to choose among seven vendors. Luna selected it on two Le Monde shell draws, but did not select it after the Telegraph hard failure. The registered stop rule ended the screen before its ordinary control. No alternate-Read production authority was earned. [L11]

The existing LinkUp default itself had earned earlier bounded evidence against Exa’s known-URL Read weaknesses. Keeping it did not mean claiming it was universally best. The project could recognize a real capability in a specialist configuration while declining to turn a six-URL bake-off into a domain router. [R10], [L10]

For a small application, this is an uncomfortable but legitimate endpoint. Some source access remains unreliable. The appropriate result may be a useful limitation rather than another subsystem. It would also be wrong to blame access for every failure: the appendix episode involved material already acquired successfully.

<a id="managed"></a>
## 10. Buying managed research without surrendering evidence

The Exa Deep investigation reopened a product question that the earlier failures made more—not less—reasonable: must ScryRaven own every internal search decision?

The answer reached in discussion was no. The essential product boundary was not “we personally orchestrate every query.” It was “we do not accept someone else’s synthesized answer as the underlying evidence.” A managed service could expand queries, explore directions, and return exact source excerpts or useful targets. ScryRaven could still own task interpretation, source custody, independent semantic evaluation, final synthesis, and citations.

That possibility was investigated rather than dismissed as becoming a wrapper. It also was not assumed to work merely because the provider described sophisticated orchestration.

### 10.1 Full-question probes separated speed from warrant

The first MD-80 probe intended to compare Deep and Deep Reasoning. The Deep capture failed; the surviving records did not prove the complete two-mode observation. A later specifically authorized recovery call preserved plain Deep. The failed original record was not erased. [L14]

Deep Reasoning returned in 14.702 seconds with a provider-reported cost of $0.015. It proposed a 2.3-cent passenger-mile difference using an MD-80 carrier average and a 777-200 available-seat-mile value. The arithmetic was not the central error. The denominator and aircraft applicability were.

Plain Deep’s recovery took 9.191 seconds and reported $0.012. It refused a numerical difference more appropriately, but its final qualitative ranking still outran the supplied evidence. Neither observation established a material source-discovery improvement over the preserved ScryRaven record. These claims concern the supplied probe reports, not an independently rerun comparison. [L14]

The cheapness remained interesting, but one provider call was not a complete comparable ScryRaven product turn. ScryRaven’s longer runs included semantic reassessment, fetches, local inspection, and final Answer. Subtracting those times without comparing delivered capability would be misleading.

### 10.2 A discovery-burst test failed a narrower substitution claim

The next test asked whether one Deep request using an exact historical Search query could reproduce the consequential source opportunities reached by a bounded sequence of ordinary searches. It tested three task families with six requested results and exact Highlights, excluding generated synthesis.

It failed its gate. MD-80 recovered the replacement-model source but missed the substantive historical 777 study. Passport found the correct base-engine neighborhood but missed the later GE specification. Dorothy returned much of the generic recruitment frontier but did not establish the selection; the historically decisive posts had come through lexical discovery, not ordinary Exa. No product treatment ran. [L15]

The right inference was limited: this type-only, historical-query substitution did not demonstrate equivalent-frontier compression. It did not establish that every managed-search objective or hybrid sequence was ineffective.

### 10.3 The user’s correction changed the question legitimately

The user pointed out that a broader search service might deserve a research objective rather than a keyword string optimized for an ordinary query. It might also provide a head start rather than replace the whole process. One Deep pass followed by ScryRaven’s targeted follow-up could be useful even if the first result was incomplete.

Those are different hypotheses. Preserving the earlier negative result while defining a new one was not moving the goalposts. Quietly relabeling the old result as successful would have been.

The subsequent query/depth calibration supplied the missing separation between **what the provider is asked** and **how much provider search effort is selected**.

<a id="query-language"></a>
## 11. Learning to use Exa on its own terms

### 11.1 A small factorial calibration finally separated the variables

Four preserved research needs were tested contemporaneously: a BIPM lookup, Passport, St. Dorothy’s, and MD-80. Each received the historical query and a natural-language evidence objective under both Auto and Deep. Result count and content settings were held consistent. The objective expressed information available at the frozen state rather than inserting later-discovered answers or URLs. [L16]

| Need | Objective-style Auto | Objective-style Deep | What was actually learned |
|---|---|---|---|
| BIPM lookup | Sufficient | Sufficient, with no consequential extra benefit | More provider work did not improve an already-complete narrow lookup. |
| Passport | Better program applicability, range still absent | Relationship and GE thrust datasheet together | A provider could sometimes compress a genuine discovery dependency. |
| St. Dorothy’s | Still vacancy/interim dominated | Better candidate qualifications and historical experience | Discovery advanced, but the selection relationship remained unproved. |
| MD-80 | Methodology/applicability tradeoff; useful numeric opportunity lost | Both important historical cost-source opportunities | Better material for subsequent judgment, not a matched passenger-mile answer. |

Within Deep, objectives were better on all three complex cases in these draws; Auto’s formulation results were mixed. Objective-style Deep added roughly five to ten-and-a-half seconds and half a cent over Auto per case. These were observed request deltas, not completed-product savings. Among the three complex needs, only Passport’s full frozen information need was satisfied; the simple BIPM lookup was also sufficient. [L16]

The transformation changed more than grammar. It altered query length, constraint expression, site syntax, and resulting highlight selection. The experiment supported a composite interface technique; it did not prove that natural language is universally superior to exact terms or that Exa is purely semantic rather than hybrid.

### 11.2 Routing remained a separate problem

Six frozen Luna choices tested focused Auto, broader Deep, and no Search when a retained source should be read. Five matched the registered expectations, and the generated objectives were acceptable. Dorothy chose Auto with an intelligible explanation: one organization, one announcement. The observed provider frontier favored broader exploration, but Deep itself still did not establish the appointment. [L16]

This was not an 83% production routing reliability estimate. The states were related, partly extrapolated, and used a small experimental decision surface rather than the full Research loop. The project did not integrate Auto/Deep routing on that evidence.

### 11.3 PR #665 changed formulation, not orchestration

The adopted change was deliberately smaller: generic Exa Search should express a concise natural-language evidence objective, retaining consequential known constraints and avoiding an assumed answer. The existing Research owner wrote that query directly. There was no rewriting model, new field, transport mode, or extra semantic call. Lexical source discovery remained separately available. [R18]

Twenty live generic queries were classified: eighteen objective-aligned, one acceptable neutral, and one misdirected confirmation of an unestablished appointment. BIPM remained a correct one-Search lookup. Passport established the relationship and published range. Dorothy remained a weaker partial after failed source Reads. MD-80 did not shorten its Research trajectory. The original aircraft Answer was interrupted by faulty evaluation accounting and later recovered separately over its preserved Evidence. [L17], [R18]

The final promotion accepted a faithful, provider-aligned query convention under a bounded regression standard. It did **not** claim statistical superiority, fewer calls, or general latency improvement. That qualification belongs in the portfolio story as much as the successful merge.

The endpoint is consequently precise: **natural-language generic Search guidance shipped; Deep routing did not**.

<a id="industry"></a>
## 12. What industry had built—and what transferred

This section is outside research, not additional ScryRaven experimental evidence. Primary technical sources were checked for this edition. Vendor evaluations describe the vendor’s conditions; papers describe their evaluated tasks. Transfer judgments below are this retrospective’s analysis.

### 12.1 Perplexity: the retrieval stack is substantial engineering

Perplexity’s published search-API account describes hybrid lexical/semantic candidate retrieval, filtering, staged ranking, cross-encoder reranking, and retrieval of sub-document spans. Parsing and refresh behavior are parts of the system, not cosmetic preprocessing. [X01]

The relevant contrast is not “a large company has a better prompt.” It owns substantial infrastructure before the answer model sees material. ScryRaven could buy access to that class of capability or borrow particular boundaries, but recreating the index, ranking, parsing, and serving loop would be a different business and maintenance commitment.

This does not establish anything about undisclosed private controller behavior. Nor does it justify folklore about a fixed universal context limit. The transferable principle is to make retrieval produce useful material before expensive downstream reasoning—not to reproduce a speculative product diagram.

### 12.2 Query-aware extraction: a small returned snippet can have a large training system behind it

Perplexity describes a bidirectional encoder with a compression head that selects source material rather than generating a replacement summary. Its account reports 750,000 labeled query–document training pairs and a distilled production path with p99 latency below twenty milliseconds. In its BrowseComp setup, it reports 10–70% lower query-level token usage and accuracy gains of roughly 4–4.81 percentage points across settings. [X02]

These numbers refer to different quantities: training examples, serving latency, and downstream evaluation gains. They are not evidence that the reported improvement came from an assumed 100,000-search test.

For ScryRaven, the implication is practical: learned selection can be fast and useful, but a new generative “summarize this packet” call is not an equivalent implementation. Training data, exact span recovery, distillation, serving, and downstream measurement are part of what made the reported technique work. The observed high-context setting sometimes requiring fewer total tokens also cautions against blind shrinkage.

### 12.3 Search-as-Code: useful where code can remove semantic round trips

Perplexity’s Search-as-Code design exposes retrieval, filtering, ranking, fan-out, and result rendering through a sandboxed programmatic interface. Intermediate results can stay outside the main model context. Its reported 85.1% token reduction—from 288.7k to 42.9k—came from a specific vulnerability-record task, not a universal research-speed multiplier. [X03]

The transfer question is which ScryRaven operations can actually be completed mechanically. Filtering structured rows or combining independently selected sources may fit. Interpreting whether an aircraft-cost estimate belongs to the requested population still requires semantic judgment. Code can also call models, so hiding several model invocations behind one program does not remove their cost.

The work was worth understanding, but did not justify replacing a small inspectable executor with a general code-agent platform during this investigation.

### 12.4 Anthropic: parallel research can be valuable and expensive

Anthropic describes a lead researcher with parallel subagents, particularly useful for broad tasks with several independent directions. Its engineering account also reports coordination failures, over-searching, and substantial token consumption: about fifteen times chat token usage for its multi-agent systems, compared with about four times chat for agents generally. The fifteen-times figure is **not** a comparison against a single research agent. [X04]

That is a different economic target from minimizing the cost of a small sequential assistant. Parallelism can reduce elapsed time while increasing total work. Dependencies and shared-context coordination limit how much work is independent.

The same account provides an important counterweight to evaluation pessimism: its team started with about twenty representative queries to detect large early changes. Small samples are not worthless; they simply cannot support fine-grained reliability or optimality claims.

### 12.5 Dynamic filtering: fewer input tokens can still cost more

Anthropic’s dynamic-filtering work lets its web tools use code to filter returned material before it enters context. In its reported evaluations, input use fell by 24% on average. However, price-weighted tokens decreased for Sonnet 4.6 and increased for Opus 4.6 because the extra processing has its own cost. [X05]

This is directly relevant to ScryRaven’s measurement discipline. A context intervention must count the computation that selects or compresses the context, not just celebrate the text it removes. The result supports testing complete economics, not importing a particular architecture unexamined.

### 12.6 Open pruning models are possible, not free to integrate

Provence combines learned context pruning with reranking and sequence labeling, offering an out-of-the-box model rather than requiring every adopter to train one. LLMLingua-2 uses a distilled token-classification approach to prompt compression. Both make “only a large company can attempt this” too strong a claim. [X06], [X07]

For ScryRaven, integration would still require choosing retrieval units, serving a model, maintaining source-offset mappings, and evaluating preserved qualifications. Removing words from a passage must not silently turn the remaining words into a supposedly contiguous quotation. A table value without its heading, unit, or footnote can be worse than a longer paragraph.

The constraint was therefore engineering and evaluation opportunity cost, not technical impossibility. These methods were researched; they were not implemented and falsified locally.

### 12.7 Stopping research validates the problem, not a ready-made fix

HALT treats stopping as evidence coverage over expected reasoning requirements rather than generator confidence. Its deployable condition generates requirements from the question; a separate gold-support condition is a diagnostic upper bound. It reports reduced redundant retrieval while largely retaining exact-match performance on its benchmarks, and declines to stop when coverage cannot be verified. [X08]

That is relevant but incomplete for a question whose best answer may remain partial. Waiting for every requirement to be supported does not itself explain when further research is no longer worthwhile.

Stop-RAG instead learns value-based retrieval control from completed trajectories. Its mechanism directly addresses whether another retrieval is useful, but requires training evidence and evaluated policy behavior; it is not reproduced by adding an `expected_gain` string to a prompt. [X09]

Both approaches were research references, not demonstrated ScryRaven remedies.

### 12.8 Tool-grounded critique differs from a second opinion

CRITIC studies self-correction supported by tool interaction and external feedback. That is not equivalent to a reviewer seeing the same packet and returning another unsupported judgment. [X10]

Google’s Sufficient Context work distinguishes missing adequate support from a model failing to use adequate support. That distinction closely matches ScryRaven’s separation of acquisition and semantic-use failures. It does not supply a stopping policy for every unresolved open-web question. [X11]

The transfer lesson is to ask what new evidence or authority a reviewer contributes. A new role label alone is not independent verification, as the local parking-brake result illustrated.

### 12.9 Continuation and caching are accounting mechanisms, not free cognition

OpenAI’s conversation-state documentation states that previous input remains billable when chained with `previous_response_id`. Prompt caching depends on matching prefixes and actual cache behavior; a separate reviewer and Answer with different request structure cannot assume a shared cheap context merely because they discuss the same sources. [X12], [X13]

Thus a “Research episode” may simplify orchestration or improve continuity without eliminating underlying model submissions. A cache may reduce input cost without fixing source selection or reasoning output. These are useful tools, but their benefit must be measured at the provider-request boundary.

### 12.10 Exa: a semantic interface still needs calibration

Exa’s Search guide, checked for this edition, asks for natural-language descriptions including subject, source type, and relevant time. It distinguishes ranked source results from optional generated synthesis. Its Deep documentation describes query expansion and iterative evidence gathering, with synthesized output separately controlled. [X14], [X15]

That supports the legitimacy of ScryRaven’s query/depth calibration, not a universal rule that longer queries or deeper modes are better. Exact terminology can remain valuable; broad objectives can be useful or noisy. The local experiments—not vendor categories alone—determined the bounded result adopted in PR #665.

### The industrial lesson at the right scale

The more sophisticated approaches were not all interchangeable substitutes for the current loop. Some needed training trajectories; some needed a local serving component; some bought latency with parallel token spend; some belonged to a provider’s index and parsing infrastructure; some were immediately usable as API capabilities.

A solo project’s realistic advantage was not matching every layer. It was keeping the product’s evidence boundary clear enough to evaluate and selectively consume outside capability. That is an architectural choice, not an admission that the product has no independent value.

<a id="evaluation"></a>
## 13. What small-sample engineering can legitimately establish

ScryRaven did not have the traffic, training pipeline, or representative evaluation volume required to optimize a research policy statistically across a broad user population. That limited its claims. It did not make disciplined engineering impossible.

### Different claims require different evidence

| Claim | Suitable evidence | What it cannot establish by itself |
|---|---|---|
| The catalog transformation preserves every logical value | Exact inversion, boundary cases, property-oriented tests | Equivalent model decisions |
| The controller can perform an evidence-dependent transition | A preserved live witness where new evidence changes the next operation | Frequency across arbitrary questions |
| A passage actually reached Answer | Exact packet/exposure record and source identity | Comprehension or correct synthesis |
| A prompt changes query behavior | Frozen and ordinary emitted queries, classified without rewriting them | General answer-quality improvement |
| A change reduces end-to-end cost | Comparable completed-run measurements including every call | A stable population effect from one draw |
| A stopping rule is safe | Both justified-stop and justified-continue cases, then broader validation | Safety merely because it reduces calls |
| A provider mode is a better generic default | Representative quality/latency/cost evidence | A conclusion from one particularly favorable query |

The project produced meaningful evidence in the first several rows. It did not pretend they automatically established the last row.

### Frozen states were microscopes, not production substitutes

A frozen packet isolated a decision: given this evidence, can the model select the acquired appendix, retain the controlling metric, or stop on a lookup? That was far cheaper and more interpretable than rerunning an entire trajectory.

But the full loop changes the next state after every decision. A locally better action may lead to different acquisition; additional evidence may distract; a later retention choice may undo an earlier success. The stronger-model result made the gap between a one-step screen and trajectory competence impossible to ignore. [L12]

### Historical controls saved money and weakened causal attribution

The project often had multiple preserved runs of the same development question. Reusing them avoided repeatedly purchasing an untreated baseline. That was reasonable for bounded regression context and descriptive comparisons.

It could not eliminate changes in the index, publication state, provider extraction, models, prompt versions, cache conditions, or trajectory. The latest Exa formulation record therefore reported exact comparators and their differences rather than silently assembling a favorable “baseline” from several runs. [R18]

For query/depth calibration, contemporaneous provider pairs were appropriate because the specific question was about two query formulations and two modes. Even there, one draw did not remove stochastic retrieval or within-run drift. [L16]

### A development question stops being held out

BIPM, Passport, Dorothy, and MD-80 became deeply understood development cases. They remained useful for preservation and diagnosis. They were not fresh tests of generalization merely because a new branch ran them.

Repeatedly choosing prompts or thresholds against those same states would eventually optimize the test relationship rather than establish broad competence. The project’s stop rules helped limit that temptation, but a preregistered rubric could itself be too restrictive. A plausible unexecuted redirect should not be called harmful merely because it failed a FINISH label. A different source can satisfy an obligation even when the expected URL is missing. [L13], [L15]

The lesson is to preserve the scored outcome **and** its interpretive limits. Keeping the original label does not forbid explaining why it supports a narrower conclusion.

### Negative results were valuable when they closed specific hypotheses

“Two thousand characters did not earn the default” is useful. “Less context can never help” is not supported. “This six-state Luna reviewer did not earn a product test” is useful. “Reviewers cannot work” is not supported. “Type-only Deep substitution failed this screen” is useful. “Delegated acquisition is permanently invalid” was contradicted as a blanket conclusion by the later calibration’s narrower positive signal.

The project’s best decisions treated experiments as evidence about mechanisms, not as referendums on the creator’s ambition.

### No claim of having exhausted the parameter space

The work explored a substantial, relevant neighborhood of feasible interventions. It did not enumerate all prompts, models, retrieval modes, learned policies, or attention designs. Calling a lane “locally exhausted” was an allocation decision under current evidence and resources, not a theorem.

This matters for a portfolio account. The growth was learning to stop an unproductive line without declaring the problem solved or impossible—and to reopen it only when the hypothesis actually changed.

<a id="harness"></a>
## 14. The test harness is part of the experiment

Some of the most instructive failures were not model failures at all.

The original Exa Deep observation lost its capture, with a later offline diagnostic reproducing a Unicode-output issue. The exact live exception was not retained, so the report could not claim more than the surviving evidence supported. A separately authorized recovery repaired the missing observation without pretending the original response had been saved. [L14]

The query/depth calibration initially encountered local preparation failures caused by a helper named `inspect.py` shadowing the standard library. The preserved diagnostic established failure before network transmission. Those attempts were not counted as billed Exa requests. [L16]

Most consequentially, the evidence-objective product campaign used a reservation wrapper that conservatively priced Answer at inflated accounting rates and reserved the full output allowance. The first request’s reservation remained outstanding until semantic completion. A calculator continuation triggered another reservation and exceeded the wrapper’s projection, even though the evidence did not establish that actual spend had reached the nominal cap. [L17], [R18]

That stopped the MD-80 final Answer. The project did not infer a semantic failure, increase product budgets, or rerun all eleven Research calls. It recovered only the Answer over preserved source material. Because the original opaque provider continuation envelope was absent, the recovery was a **fresh frozen-packet invocation**, not a byte-exact resume. It preserved the original interrupted record and recorded the recovered result separately. [R18]

Three engineering lessons follow.

**A safety mechanism can contaminate the measurement it is intended to protect.** Budgets should bound exposure without accidentally changing the underlying product behavior being tested.

**Failing locally is not the same as consuming a provider attempt.** Attempt accounting needs clear boundaries and retained receipts.

**Exact evidence preservation makes limited recovery possible.** The ability to reconstruct what Answer was supposed to read avoided paying for a whole new research trajectory and changing the experiment’s source basis.

The project also learned that AI-assisted planning can overproduce evaluation machinery: giant briefs, overly rigid gates, extra local wrappers, and repeated permissions can become part of the cost. Keeping scope narrow is not only about production architecture. It also applies to the experimental process used to change it.

<a id="snapshot"></a>
## 15. State of the project at the time of writing

This is a dated endpoint, not an instruction for future changes.

At repository snapshot `8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6`, after PR #665:

| Surface | State at this edition |
|---|---|
| Ordinary semantic topology | One Research owner and one fresh Evidence-first Answer owner. |
| Generic discovery | Exa Auto, six requested results, Dynamic/high Highlights; Research writes natural-language evidence objectives. |
| Lexical discovery | Research-selectable Serper navigation for the appropriate source need. |
| Known-URL Read | Existing LinkUp static Fetch; no automatic alternate materializer. |
| Retained sources | Immutable acquired material, versions, and locally recoverable exact views. |
| Current context | Reconstructed packets, compact catalog tables, bounded source attention, generated understanding kept non-evidentiary. |
| Answer | Independent source evaluation, literal readings, citation checks, bounded deterministic calculator. |
| User settings | Research/Answer model, reasoning, and tier resolved from shipped defaults or complete per-user override. |
| Shipped model defaults | Research Luna/high/Fast; Answer Sol 6.1/medium/Fast. |
| Reported current user-local override | Answer Sol 6.1/high/Standard; Research unchanged. This is not a claim that the shipped default changed. |
| Deep / Deep Reasoning | Provider observations and calibration only; not an ordinary Research-selectable production mode. |
| Parking brake / displacement critic | Not promoted. |
| Evidence of general reliability | Not established by the small development corpus. |

The snapshot’s strongest promises concerned accountable evidence use and demonstrated adaptive behavior. Its open limitations included long difficult trajectories, source-access failures, semantic retention and stopping, final qualification coverage, and long-session scaling. The absence of general reliability evidence should not erase demonstrated capability, and demonstrated capability should not erase those limitations. [R10], [R11], [R17], [R18]

### What did not become a product requirement

No result made a particular model, provider, prompt, graph, cache policy, or timeout sacred. Several had already been replaced. Equally, no failed experiment created a permanent prohibition against all future work in its category.

A future reader should use the library to ask: what was actually tested, on what state, against what obligation, with which result and limitation? The answer is historical input to a new decision, not standing authority to resurrect a design.

<a id="takeaways"></a>
## 16. What the work demonstrates

### The product became more capable by becoming more explicit about fewer boundaries

The simplification was not an abandonment of rigor. It concentrated rigor where code could enforce it—identity, exact material, valid references, persistence, budgets—and left semantic interpretation visible rather than burying it inside a proliferation of admission and status objects.

The evidence does not prove that small architectures always win. It shows that this project recovered a clearer relationship between implementation and product behavior when it could observe one Research owner revise a task from sources and one Answer owner independently use those sources.

### Source custody made negative results actionable

The project could distinguish “did not find,” “did not fetch,” “did not expose,” “did not preserve,” and “did not express.” That allowed a local appendix probe, a retained-source follow-up improvement, and an Answer-only recovery. It also prevented blaming a retrieval component for every downstream omission.

That diagnostic ability is part of the delivered engineering, not just paperwork surrounding it.

### The interface to a tool is part of the research system

Natural-language Exa calibration became promising only after separating query formulation from search depth. A correct tool description and query convention were lower-complexity interventions than building another controller. The adoption still did not magically fix repetition or guarantee a shorter trajectory.

The lesson is neither “prompts solve everything” nor “prompts never matter.” It is to identify the exact decision or interface behavior the prompt is supposed to change, observe whether it changes, and avoid assigning it credit for unrelated successes.

### A partial answer can be a successful product outcome

The project’s aviation work repeatedly showed why a plausible number could be worse than a qualified explanation. But honest partiality did not excuse avoidable omissions or abandonment of a promising source. Good partial answers still require active judgment about what was established, what remains incompatible, and what further information would change the result.

That is a richer product goal than either maximizing answer rate or maximizing refusal caution.

### AI-assisted development still needs a human theory of the product

The implementation process used coding agents and model-assisted review, but the important choices were not merely code generation: choosing a support boundary, insisting on a real dependency witness, recognizing a flawed benchmark, separating component and whole-product claims, declining expensive infrastructure, and refusing to let failed experiments become either shame or doctrine.

The project owner also challenged the experimental framing when a provider was evaluated as a transparent replacement rather than as a different instrument. That led to a better-designed calibration and a modest adopted improvement. The value of AI assistance was amplified by those decisions, not substituted for them.

### The honest portfolio claim

ScryRaven demonstrates a capacity to build, inspect, simplify, measure, and revise a nontrivial AI application under realistic constraints. It also demonstrates the discipline to preserve an inconvenient result and state what it does not prove.

It does not demonstrate a universally optimal researcher, an industrial-scale learned policy, or a victory over commercial systems. It does demonstrate something worth showing:

> A capable research product whose creator can explain how its answers are grounded, where its costs arise, which improvements survived contact with evidence, and why its remaining limitations are not all the same problem.

“And Counting” is not a promise to keep testing forever. It leaves room for new evidence without turning this edition into a roadmap.

<a id="experiment-library"></a>
## 17. Experiment library

This index records dispositions, not permanent instructions. “Rejected” refers to the tested candidate. “Inconclusive” is not a negative reliability estimate. “Adopted later” preserves the distinction between an original campaign gate and a subsequent product decision. Local-only records are identified in the source register; they are not implied to be publicly downloadable.

### Architecture and capability

| ID | Question / intervention | Observation or disposition | What it does not establish | Sources |
|---|---|---|---|---|
| E01 | Formal graph admission, component recovery, and scheduler leases | Extensive deterministic authority/lineage work; later retired from the active product lineage. | That graphs are inherently wrong, or that passing contract tests proves research quality. | [R02], [R03], [R04], [R05] |
| E02 | Reset and walking skeleton | Small foundation followed by real narrow factual Research/Analyst/Author product success. | Broad multi-component competence at that stage. | [R05], [R06] |
| E03 | Investigator behavioral campaign | Useful narrow answers; repeated source-action/stopping failures persisted after two interventions. Abandon/rethink recommendation. | Universal failure of a concentrated semantic controller. | [R07] |
| E04 | Initial V2 two-owner implementation | Real custody, sessions, local inspection, and exact readings; intended broad capability not met in the initial campaign. | That two-owner topology could not later work. | [R08] |
| E05 | Observation/inference/scope declarations | Recorded as a failed contract intervention; retained as development history, not active semantics. | That any explicit scope representation is useless. | [R20], [R10] |
| E06 | Capability ladder and mainline supersession | Bounded factual, premise-restraint, retained-follow-up, and counted dependency witnesses; current two-owner path promoted. | Universal recursive reliability, particularly the separately unestablished Level-6 frontier. | [R09], [R10] |
| E07 | Source-first Answer readings and coverage | Literal membership became enforceable; bounded coverage work improved preservation in supplied packets. | Semantic entailment proof, or repair of sources omitted before Answer. | [R08], [R15] |
| E08 | Model-role ownership/configuration | Runtime selects roles; shipped defaults and per-user settings separated; local amendments need no PR. | A quality improvement from a model choice merely because it is configurable. | [R17] |

### Context, continuity, and control

| ID | Question / intervention | Observation or disposition | What it does not establish | Sources |
|---|---|---|---|---|
| E09 | Prior-cited exact Evidence in follow-up input | Reduced local rereading and Research work in bounded observations; retained as product behavior. | General long-session scaling or automatic relevance of all prior material. | [R16] |
| E10 | Packet layout and `purpose` removal | Bounded preservation checks; less procedural representation carried forward. | A general latency or intelligence gain. | [R10] |
| E11 | Search novelty/history and expected yield | Two model-facing campaigns mixed/inconclusive; numerical diagnostics retained, model-facing history removed. | Novel bytes equal useful information; all history-based control is ruled out. | [R14] |
| E12 | Failed external-Read receipts | Safe turn-local operation memory retained. | A semantic adequacy detector or automatic retry policy. | [R10], [R11] |
| E13 | Task–evidence-fit instruction and contract review | Wording treatment did not show clear improvement; existing contract could express correct states. | An ideal prompt, or inability to benefit from a genuinely new interface instruction. | [L01] |
| E14 | Optional scout hierarchy | Useful discovery arrived too late in a key treatment; optionality did not impose helpful ordering. | Scouting has no useful content. | [L01], [L18] |
| E15 | Mechanical first-search orientation | Promising ambiguous-discovery observation; generic architecture rejected after lookup overhead screen. | Thin navigation never helps complex tasks. | [L01] |
| E16 | Uniform 4,000→2,000 Search excerpts | Less returned text; more aggregate Research input/calls; rejected as default. | Smaller context can never help; every trajectory difference was caused by excerpt size. | [L02] |
| E17 | Offline trajectory-cost decomposition | Additional calls dominated the observed token increase; repeated state substantial secondary cost. | A causal decomposition of stochastic model behavior or exact field-token accounting where packets were missing. | [L02] |
| E18 | Lossless catalog tables | Exact inversion and substantial same-state serialization reduction; initial campaign inconclusive; later adopted in PR #662. | Improved semantic retention or universal whole-run savings. | [R12], [L03], [L04] |
| E19 | Provider-native Dynamic Highlights | Source allocation/custody evidence; original whole-product gate inconclusive; later adopted in PR #663. | Better stopping or every final qualification preserved. | [R13], [L05] |
| E20 | MD-80 acquisition-sufficiency review | Useful partial support existed early; acquired common-data appendix remained uninspected. | R2 is always the best stop, or the requested scalar was already available. | [L06] |
| E21 | Acquired-source exploitation counterfactual | Existing local operations actually reached Appendix B; no missing basic operation established. | Guaranteed semantic use of the returned table. | [L07] |
| E22 | Retention/attention replay | Semantic omission separated from pending-first displacement; simple carry-forward insufficient for later omission. | A uniquely established allocator redesign. | [L08] |
| E23 | Conditional displacement receipt | Control and both treatment decisions omitted the controlling source; candidate rejected. | Every possible signal or retention mechanism cannot help. | [L09] |
| E24 | Luna/Sol/Gemini controller comparison | Sol and Gemini improved selected frozen decisions; Sol full-run premium not justified; no Gemini product run. | Harness causation, universal model rankings, or Gemini end-to-end failure. | [L12] |
| E25 | One-time Luna parking brake | Two continuation controls passed; four registered intervention criteria failed; stopped before product runs. | Actual avoided-call economics, live harm, or universal critic failure. | [L13] |

### Acquisition, providers, and query formulation

| ID | Question / intervention | Observation or disposition | What it does not establish | Sources |
|---|---|---|---|---|
| E26 | LinkUp primary Read against earlier Exa weaknesses | Bounded rescues and controls supported the default change. | LinkUp is best on every page or source class. | [R10] |
| E27 | Six-URL/eight-configuration materialization bake-off | No universal winner; hard-page gains and regressions; PDF/community limits persisted. | A monotonic price ladder or reliable publisher router. | [L10] |
| E28 | Provider-opaque alternate Read action | Two Le Monde shell decisions selected alternate; Telegraph did not; ordinary control not reached. | General selection reliability or an end-to-end rescue benefit. | [L11] |
| E29 | Full-question Exa Deep/Deep Reasoning probes | Fast, inexpensive reported requests; flawed synthesis; lost capture recovered separately. | Comparative full-product efficiency or safe generated-answer authority. | [L14] |
| E30 | Type-only Deep discovery burst | Three cases failed equivalent-frontier gate; no product treatment ran. | Failure of every objective-formulated managed-search workflow. | [L15] |
| E31 | Query style × Auto/Deep calibration | Objective-style Deep improved complex frontiers; Auto mixed; one complex case source-sufficient; routing screen mixed. | A grammar-only effect, generic Deep default, or live routing reliability. | [L16] |
| E32 | Evidence-objective Search, PR #665 | Strong query adherence; BIPM/Passport successes; complex trajectories mixed; Answer-only recovery completed preservation check. Guidance adopted. | General cost/latency improvement, or a completed original interrupted MD-80 run. | [L17], [R18], [R22] |

### How to retrieve an earlier lesson

Use the stable library experiment ID (E01–E32), report title, and source entry together. Source-material IDs such as E20 or E55 can reuse that notation, but belong only to their named historical run; they are not global identifiers. A frozen-state screen, a provider-only probe, an offline replay, and a full product run are different forms of evidence. Before reusing a result, read its scope and its “does not establish” column.

<a id="source-register"></a>
## 18. Source register and evidence-access notes

### Provenance of this edition

Documentation verification checked repository documents and retired implementation history through local Git objects, and checked the cited PR metadata and descriptions through GitHub. PR #665 is merged at the stated edition SHA, which also matched fetched `main` when this documentation branch was prepared. Repository-document links are pinned to that snapshot, so later changes to `main` do not silently change the historical account. PR descriptions establish what those work items reported and changed; they are not independent product benchmarks.

The supplied draft synthesized local reports and author handoffs. Documentation verification first located the matching report families, then read their preserved sanitized reports, adjudications, metric summaries and provenance indexes. It did not inspect raw provider payloads, hidden reasoning, databases, caches, raw prompts, or unrelated private evaluations, and it ran no new experiment or ScryRaven research turn. Local-only locators below are repository-relative reference metadata shown as text, not public download links. L01’s separate contract-review account and L18’s original addendum remain author-handoff limitations where no exact original report was located; related records are identified without pretending to replace them.

Industry sources were checked separately as public primary material. Their reported performance is attributed to their authors, and the applicability assessment is analysis for ScryRaven. Direct English Perplexity page retrieval was unavailable during documentation verification; indexed publisher text and the publisher’s localized editions corroborated the cited architecture and measurements. Those access limits do not constitute independent reproduction of the vendor’s experiments. This edition does not claim knowledge of any provider’s undisclosed private system. External documentation links are mutable, unlike the pinned repository links; these statements describe the sources checked for this edition, not future API recommendations.

**Verification corrections for the October 1, 2026 edition:** the source register now records the reports actually located and checked, including L07’s canonical family and provenance index; the task–evidence fit screen is clarified as four paired cases and eight total decisions; the calibration’s sufficiency sentence explicitly separates the simple lookup from the three complex needs. Consecutive source citations are separated so each resolves to its own reference. No historical experiment disposition or principal conclusion was changed, and no new product validation is claimed.

### Repository and implementation history

- **R01 — Initial public README, May 27, 2026.** Pinned to `bdfa67173238ef9fc8ceb8e2d8d92d8e05636d2b`. Establishes an existing private prototype released as a public snapshot, its pipeline and UI, and its explicit prototype status. [Open R01][R01]
- **R02 — PR #472: RunKernel graph admission.** Ref-only deterministic contracts and the distinction from actual graph execution. [Open R02][R02]
- **R03 — PR #480: bounded dynamic graph recovery.** Recovery, lineage, amendments, and serial resynthesis; explicitly bounded/offline evidence. [Open R03][R03]
- **R04 — PR #483: graph scheduling leases.** Grant/commit/admission/completion and stale authority handling; runtime parallelism disabled. [Open R04][R04]
- **R05 — PR #623: retire the v1 active tree.** Reset scope and preserved historical tag. [Open R05][R05]
- **R06 — PR #624: first walking skeleton.** Narrow live product successes and explicit broader limits. [Open R06][R06]
- **R07 — Investigator behavioral validation.** Seventeen submissions, two interventions, useful results and persistent failures. [Open R07][R07]
- **R08 — V2 implementation/development validation.** Initial two-owner candidate, source-first repair, ten submissions, preserved failures. [Open R08][R08]
- **R09 — Mainline Semantic Supersession 01.** Accepted two-owner lineage, ordinary dependency witness, retained follow-up, qualified acceptance. [Open R09][R09]
- **R10 — CURRENT.md at the edition snapshot.** Dated source for broader capability, latency, provider, and remaining-limit observations. This link is historical; future operating truth is the then-current file. [Open R10][R10]
- **R11 — Ordinary Research / Evidence-first Answer architecture.** Custody, attention, tool, model, cache, Answer, and session boundaries at the snapshot. [Open R11][R11]
- **R12 — Catalog Table Integration 01.** Lossless representation evidence and later integration scope. [Open R12][R12]
- **R13 — Dynamic Highlights Integration 01.** Provider request, exact-source treatment, and distinction from original campaign disposition. [Open R13][R13]
- **R14 — Search Novelty Receipts 01.** Two model-facing campaigns, removed model history, retained diagnostics, and lost-draw limitation. [Open R14][R14]
- **R15 — Answer Coverage Retention.** Direct-Answer preservation observations and source-reading limits. [Open R15][R15]
- **R16 — Latency Consumption 01.** Effort/tier experiments and exact prior-cited follow-up exposure. [Open R16][R16]
- **R17 — PR #664: role configuration ownership.** Shipped defaults, per-user override, coherent resolution, and next-turn changes without Git. [Open R17][R17]
- **R18 — Exa Evidence-Objective Search 01.** Prompt-only implementation, ordinary observations, interruption, and separately recovered Answer. [Open R18][R18]
- **R19 — PRODUCT.md at the snapshot.** Product thesis, source authority, user premises, and implementation replaceability. [Open R19][R19]
- **R20 — V2 Scope Contract Validation.** Historical scope/observation/inference intervention; not active architecture. [Open R20][R20]
- **R21 — Local Evaluation Corpus.** Repository guidance on preserved development evidence. [Open R21][R21]
- **R22 — PR #665.** Publication and merge of evidence-objective Search guidance; snapshot endpoint. [Open R22][R22]

### Supplied local reports and handoffs

All locators in this subsection are **local-only**. They name preserved, ignored artifacts relative to the owner’s checkout; a public clone does not contain them. The article summarizes their bounded results so readers do not need private packets to understand the conclusions. Verification read summary evidence, not complete source-body collections or original model/provider exchanges.

<a id="l01"></a>
**L01 — Search/orientation strategy handoff and related campaign records.** The supplied draft’s historical narrative covers novelty, task–evidence fit, contract review, optional scouting, mechanical orientation, lookup tax, and the France/Wayne/Shoresy cases. Verification checked `local-evals/campaigns/research-task-evidence-fit-01/REPORT.md`, `thin-to-deep-acquisition-ordering-01/SUMMARY.md`, `orientation-phase-falsification-01/SUMMARY.md`, and `orientation-architecture-resolution-01/SUMMARY.md` under the same campaigns directory, together with public R14. These corroborate the eight-decision prompt screen, late scouting, and the separate complex-case and lookup-tax outcomes. The separate contract-review conclusion remains an author-handoff account: no exact original review report was located. Historical narrative is not new execution authority.

<a id="l02"></a>
**L02 — Search Excerpt Density 01 and Research Trajectory Cost Decomposition 01.** Verified sanitized `REPORT.md` records in `local-evals/runs/search-excerpt-density-01/` and `local-evals/runs/research-trajectory-cost-decomposition-01/`. They support the four-pair measurements, thirty-five Research calls, descriptive count/size decomposition, and unavailable full historical packet-byte limits. The same underlying trajectories recur in later reviews; they are not additional independent trials.

<a id="l03"></a>
**L03 — Packet / State Representation Architecture Review 01.** Verified `local-evals/runs/packet-state-representation-review-01/REPORT.md` and located `artifact-manifest.json`. Reconstructed packets, exact logical round trips, and explicit clock/byte availability limits support same-state representation savings, not whole-run savings.

<a id="l04"></a>
**L04 — Catalog Table Representation Experiment 01.** Verified `local-evals/runs/catalog-table-representation-01/REPORT.md`; the family also preserves its manifest and adjudications. The report distinguishes the frozen screen, three product pairs, and failed aircraft default confirmation. Public R12 documents later integration; it does not retroactively turn the original campaign into a clean pass.

<a id="l05"></a>
**L05 — Dynamic Highlights Context Allocation 01.** Verified `local-evals/runs/dynamic-highlights-01/adjudication.json` and `product-quality-adjudication.json`, with public R13 and the historical operator report `docs/operator/DYNAMIC_HIGHLIGHTS_01.md` on the preserved candidate lineage. The original inconclusive campaign is distinct from R13’s later integration. Dorothy’s acquired transition material reached Answer; its final omission was not demonstrated provider-allocation loss.

<a id="l06"></a>
**L06 — MD-80 acquisition sufficiency / question-structure forensic review 01.** Verified `local-evals/runs/md80-acquisition-sufficiency-review-01/REPORT.md`: seven trajectories and seventy-one Research calls, separating comparability, common-basis leads and retention. Aircraft source claims are reported as evaluated in that preserved material, not newly validated aviation estimates in this essay. The acquired appendix was a promising scoped common-data lead, not an established whole-family passenger-mile scalar.

<a id="l07"></a>
**L07 — Research source-action continuity / acquired-source exploitation review 01.** Canonical family resolved from the preserved report and provenance index: `local-evals/runs/source-action-continuity-review-01/`, including `REPORT.md`, `provenance.json` and `verification.json`. Those records identify the reviewed baseline, report/source hashes and nine offline local counterfactuals. They corroborate that existing scoped Find/local Read operations reached Appendix B. Captured and reconstructed inputs remain distinguished; the Dynamic trajectory’s clock snapshot was approximate. The operations are reported as previously executed offline, not rerun here, and do not establish future model behavior.

<a id="l08"></a>
**L08 — Retention / Attention Architecture Review 01.** Verified `local-evals/runs/retention-attention-review-01/REPORT.md`. It distinguishes semantic omission, pending-first mechanical displacement and the limits of latest-intent carry-forward. Correct custody and recoverability did not guarantee effective retention or Answer selection.

<a id="l09"></a>
**L09 — Retention-Displacement Receipt 01.** Verified `local-evals/runs/retention-displacement-receipt-01/adjudication.json`; `manifest.json` identifies the experiment. One control and two treatment Research submissions all omitted the controlling E30 material; the safety draw was not reached. Full packet bytes were not inspected for this edition. The frozen decision result is not an ordinary-product result.

<a id="l10"></a>
**L10 — Known-URL Read / page materialization strategy review 01.** Verified `local-evals/runs/known-url-read-strategy-review-01/REPORT.md`, which reconstructs `local-evals/campaigns/known-url-materialization-bakeoff-01/`: six URLs × eight configurations. Bounded previews, hashes, metrics and adjudications survived, not full provider bodies. API success, partial useful material and task-sufficient material remain different outcomes.

<a id="l11"></a>
**L11 — Alternate Materialization Action Screen 01.** Verified `local-evals/runs/alternate-materialization-action-screen-01/adjudication.json`; the family retains its manifest. Two Le Monde selections, one Telegraph miss and an unrun ordinary control produced an inconclusive screen. Its minimal reconstructed packets and action-capture limits remain explicit. The preceding authorization blockage used zero model calls and is distinct from the scored screen.

<a id="l12"></a>
**L12 — Research Controller Model Comparison 01.** Verified `local-evals/runs/research-controller-model-comparison-01/REPORT.md`; `MANIFEST.json` identifies the campaign. Fifteen frozen decisions and two fresh product runs support the reported model identities, costs, cache caveats and historical user-local Answer override. Model dollars use frozen rates and exclude acquisition charges; they are not invoices or current prices. The settings file itself was not inspected for this retrospective.

<a id="l13"></a>
**L13 — Research Parking Brake 01.** Verified `local-evals/runs/research-parking-brake-01/REPORT.md`, alongside its located manifest and adjudication. Six frozen reviewer calls; product testing not reached. The continuation controls were early states and did not prove safety at the proposed live checkpoint. Avoided actor calls, acquisition savings and actual whole-run benefit were unmeasured.

<a id="l14"></a>
**L14 — Exa Deep MD-80 Probe 01 and Deep Recovery.** Verified `local-evals/runs/exa-deep-md80-probe-01/REPORT.md` and its existing recovery record `DEEP-RECOVERY.md`; the family also preserves `ORIGINAL-PROBE-REPORT.md` and `RECOVERY-MANIFEST.json`. Original lost capture, Deep Reasoning observation and authorized plain-Deep recovery are separate records. The original unavailable outcome/cost remains unknown, not zero or reconstructed; generated provider synthesis is not exact underlying Evidence.

<a id="l15"></a>
**L15 — Exa Deep Discovery Burst 01.** Verified `local-evals/runs/exa-deep-discovery-burst-01/REPORT.md`, with its located `MANIFEST.json` and Stage-A adjudication. Three type-only provider comparisons failed the registered frontier gate; no product adapter or treatment run followed. Historical lexical discovery was not credited to ordinary Exa. This does not test every managed-search objective or hybrid trajectory.

<a id="l16"></a>
**L16 — Exa Query / Depth Calibration 01.** Verified `local-evals/runs/exa-query-depth-calibration-01/REPORT.md` and located its provider/routing manifests and adjudications. Sixteen contemporaneous provider calls, six frozen routing decisions and no product runs. Empty returned `resolvedSearchType` fields did not establish an internal Auto mode. Four local URL-preparation failures were shown to occur before transmission; missing measurements and unexecuted routes are not successes or zeros.

<a id="l17"></a>
**L17 — Exa Evidence-Objective Search 01, stopped bundle and separate recovery.** Verified `local-evals/runs/exa-evidence-objective-search-01/REPORT.md`, query/quality adjudications and public R18. The original interrupted MD-80 Answer remains incomplete. R18 and the separate local `recovery/REPORT.md` record the authorized frozen-packet Answer recovery; the two must not be merged into a fictional uninterrupted run. Twenty generic queries are the query-adherence denominator; physical calculator continuations are counted separately from semantic attempts.

<a id="l18"></a>
**L18 — Unconsumed Provider / Read Evidence Addendum.** Author-handoff source identified by the supplied draft; its exact original addendum was not located for verification. Related sanitized context is preserved in `local-evals/campaigns/search-surface-density-bakeoff-01/SUMMARY.md` and L10’s Read review. These corroborate distinctions among navigation, enriched acquisition surfaces and readable source material, but do not authenticate every statement in the missing addendum. This entry supports contextual provenance, not new provider recommendations.

### Public external research

- **X01 — Perplexity, “Architecting and Evaluating an AI-First Search API.”** Primary engineering account of retrieval, parsing, ranking, and evaluation. [Open X01][X01]
- **X02 — Perplexity, “Query-Aware Context Compression for Better Snippets.”** Primary vendor account of extractive compression, training, serving, and downstream evaluation. [Open X02][X02]
- **X03 — Perplexity, “Rethinking Search as Code Generation.”** Primary description and case-study measurements; not a universal savings guarantee. [Open X03][X03]
- **X04 — Anthropic, “How we built our multi-agent research system,” June 13, 2025.** Architecture, tradeoffs, evaluation practices, and limits. [Open X04][X04]
- **X05 — Anthropic, “Increase web search accuracy and efficiency with dynamic filtering,” February 17, 2026.** Model-specific quality/input/cost tradeoffs. [Open X05][X05]
- **X06 — Chirkova et al., “Provence: efficient and robust context pruning for retrieval-augmented generation,” ICLR 2025.** Public pruning/reranking research. [Open X06][X06]
- **X07 — Pan et al., “LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression,” Findings of ACL 2024.** Token-classification compression and released implementation. [Open X07][X07]
- **X08 — Roh and Han, “HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents,” version 3, August 28, 2026.** Question-generated versus gold-support stopping conditions. [Open X08][X08]
- **X09 — Park, Cho, and Lee, “Stop-RAG: Value-Based Retrieval Control for Iterative RAG,” October 2025 workshop paper.** Learned value-based stopping from completed trajectories. [Open X09][X09]
- **X10 — Gou et al., “CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing,” ICLR 2024.** External-feedback criticism, not an ungrounded second opinion. [Open X10][X10]
- **X11 — Google Research, “Sufficient Context: A New Lens on Retrieval Augmented Generation Systems.”** Context sufficiency as a distinct analysis dimension. [Open X11][X11]
- **X12 — OpenAI, conversation-state documentation.** Billing distinction for chained response input. [Open X12][X12]
- **X13 — OpenAI, prompt-caching documentation.** Prefix matching and observed cache usage; not guaranteed free replay. [Open X13][X13]
- **X14 — Exa Search quickstart/guide.** Natural-language query formulation and separation of source results from synthesis. [Open X14][X14]
- **X15 — Exa Deep Search documentation.** Iterative search and separately controlled generated output. [Open X15][X15]
- **X16 — Exa, “Dynamic Highlights.”** Provider-native extraction/allocation context for the local experiment; local effectiveness comes from R13/L05, not marketing. [Open X16][X16]

### What this source set cannot support

It cannot establish the date the private prototype first began, every historical product capability, a total project cost or labor estimate, independent reproducibility of unpublished raw traces, a universal model/provider ranking, or the internal implementation of a proprietary research product. It also cannot turn the creator’s comparative experience using other products into a controlled benchmark.

The retrospective is strongest where it connects a specific mechanism, a preserved observation, and a bounded conclusion. Where only an author-supplied handoff was available, that limitation remains part of the record.

<a id="glossary"></a>
## 19. Glossary

**Evidence:** Actual acquired source material available for support, with identity and custody. Not synonymous with a generated claim about a source.

**Navigation:** Information useful for locating or selecting sources, including candidates, URLs, metadata, and unverified generated leads.

**Attention:** The material currently presented to a model, distinct from the larger retained corpus.

**Material view:** An exact identified region of a retained source, preserving the parent and offsets rather than rewriting its content.

**Working understanding:** Generated, replaceable continuity about the task and research state. It is not factual memory with independent authority.

**Discovery frontier:** The useful source opportunities a retrieval step exposes. More URLs do not necessarily mean a better frontier.

**Semantic attempt:** An application-level reasoning responsibility invocation. It may contain more than one physical provider request, as with calculator continuation.

**Physical model submission:** An actual provider inference request. Count these separately when measuring cost and latency.

**Supported / partial / unable:** Answer postures describing what the selected support warrants, not a universal rating of the whole research trajectory.

**Mechanical bound:** A completion/safety limit. Reaching it proves neither that the answer is supported nor that no answer exists.

**Frozen-state screen:** A local decision test over preserved inputs. Useful for diagnosis; not equivalent to a fresh end-to-end run.

**Historical comparator:** A preserved earlier observation used descriptively. Changes in index, model, source state, prompt, and cache conditions limit causal comparison.

**Promotion:** A human-approved product adoption under an explicit standard. It is not synonymous with universal benchmark superiority.

**Reference-only history:** A record to consult deliberately, not an instruction that governs current execution.

---

*End of the October 1, 2026 edition. Corrections should identify their source and edition. Later experiments belong to later dated entries; they should not silently rewrite the original outcomes described here.*

[R01]: https://github.com/aidan600/scryraven/blob/bdfa67173238ef9fc8ceb8e2d8d92d8e05636d2b/README.md
[R02]: https://github.com/aidan600/scryraven/pull/472
[R03]: https://github.com/aidan600/scryraven/pull/480
[R04]: https://github.com/aidan600/scryraven/pull/483
[R05]: https://github.com/aidan600/scryraven/pull/623
[R06]: https://github.com/aidan600/scryraven/pull/624
[R07]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/INVESTIGATOR_BEHAVIOR_VALIDATION.md
[R08]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/V2_VALIDATION.md
[R09]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/MAINLINE_SEMANTIC_SUPERSESSION_01.md
[R10]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/CURRENT.md
[R11]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/architecture/RESEARCH.md
[R12]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/CATALOG_TABLE_INTEGRATION_01.md
[R13]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/DYNAMIC_HIGHLIGHTS_INTEGRATION_01.md
[R14]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/SEARCH_NOVELTY_RECEIPTS_01.md
[R15]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/ANSWER_COVERAGE_RETENTION.md
[R16]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/LATENCY_CONSUMPTION_01.md
[R17]: https://github.com/aidan600/scryraven/pull/664
[R18]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/EXA_EVIDENCE_OBJECTIVE_SEARCH_01.md
[R19]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/PRODUCT.md
[R20]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/V2_SCOPE_CONTRACT_VALIDATION.md
[R21]: https://github.com/aidan600/scryraven/blob/8f4cb39f1f8e27b2d9ee43f9e1b4c36b15c68fb6/docs/operator/LOCAL_EVALUATION_CORPUS.md
[R22]: https://github.com/aidan600/scryraven/pull/665
[X01]: https://www.perplexity.ai/hub/blog/architecting-and-evaluating-an-ai-first-search-api
[X02]: https://www.perplexity.ai/en-GB/hub/blog/query-aware-context-compression-for-better-snippets
[X03]: https://www.perplexity.ai/en-GB/hub/blog/rethinking-search-as-code-generation
[X04]: https://www.anthropic.com/engineering/multi-agent-research-system
[X05]: https://claude.com/blog/improved-web-search-with-dynamic-filtering
[X06]: https://arxiv.org/abs/2501.16214
[X07]: https://arxiv.org/abs/2403.12968v2
[X08]: https://arxiv.org/abs/2608.02009v3
[X09]: https://arxiv.org/abs/2510.14337v1
[X10]: https://arxiv.org/abs/2305.11738
[X11]: https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/
[X12]: https://developers.openai.com/api/docs/guides/conversation-state
[X13]: https://developers.openai.com/api/docs/guides/prompt-caching
[X14]: https://exa.ai/docs/search/quickstart
[X15]: https://exa.ai/docs/search/deep-search
[X16]: https://exa.ai/blog/dynamic-highlights
[L01]: #l01
[L02]: #l02
[L03]: #l03
[L04]: #l04
[L05]: #l05
[L06]: #l06
[L07]: #l07
[L08]: #l08
[L09]: #l09
[L10]: #l10
[L11]: #l11
[L12]: #l12
[L13]: #l13
[L14]: #l14
[L15]: #l15
[L16]: #l16
[L17]: #l17
[L18]: #l18
