# ScryRaven Current Truth

Status: local Linkup/Exa bake-off implementation; ordinary PRODUCT validation pending
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Baseline and decision

The authorized experiment starts from merged main
`cb6a68c0410e9506285fdb7a1c37a560c1cbc33a` on
`codex/linkup-exa-bakeoff-01`. Both failed donor branches remain untouched:
`codex/targeted-source-reading-01` at `f69198553f0b9740e365c0842afe6bcfdd1bf913`
and `codex/evidence-escalation-01` at `01c787346634660f9c595774fdfab1e48772259c`.
They were inspected, not merged or wholesale cherry-picked. PRODUCT.md is unchanged.

Eleven Linkup Standard and thirteen Exa Search/Contents comparison calls tested
USBC bowling weight, IPCC Chapter 2, NIST FIPS 197 and Saturn chronology. No product
model calls were used. EXA_API_KEY was configured in the doorman target; the broker
was not modified. Exa's first Search found useful official material for the three
primary controls. Chapter 2's estimate/rate plus Figure 2.11 supplied the very-likely
qualification without a full chapter. Linkup's actual Standard content also proved
sufficient on known-URL USBC/NIST probes and retrieved the exact IPCC 90% caption
when targeted. Linkup retained Saturn dates better than initial Exa highlights.

Exa only is the chosen posture, pending PRODUCT validation. Separate
Contents/highlights queries failed to recover some missing context and are not
retained. The fixed product path is Search/highlights, selected material, and
Contents/full text only for concrete context gaps. Linkup code/configuration/tests
were removed. Exact sanitized comparisons and reviewer metrics remain outside the
repository at `C:\tmp\scryraven-linkup-exa-bakeoff-01\provider-comparison`.

## Implemented path and unproved claims

Exactly Research -> Analyst -> Author retain semantic authority. FAST and SMART
remain gpt-5.6-luna / medium. The ordinary entrypoint, three-Analyst/six-navigation
bounds and earned 2+2 search rounds remain. Metadata is navigation; actual
highlights may be selected as material. Extractive provenance does not establish
completeness or contiguous source spans. Same-URL acquisitions share citation
identity, not independence.

Selecting already read highlights adds no relevance call. Context gaps can trigger
one full-text acquisition per successful exact URL. Text up to 32,000 characters
is exposed directly; larger bodies produce one exact packet up to 32,000 characters,
with one optional 48,000-character expansion. Parent text remains run-local.
Only useful donor packet mechanics were reused; no interactive browser survived.

Analyst owns faithful paraphrase of significant quantities, conditions, time scope,
comparison baselines and epistemic/causal strength. Findings include exact support
anchors; mechanics validate references and quote occurrence, never meaning. Author
receives anchors and the same supporting context. Model fidelity and excerpt
sufficiency remain unproved until ordinary live controls pass.

Full pytest passed 134 tests with a fresh external temporary directory after the
checkout's old pytest temporary path denied access. Focused checks, Ruff and
production AST/imports pass. No PRODUCT invocation has yet occurred here.
No push, PR, merge, provider router, persistent corpus, vector DB, crawler, general
RAG, fourth owner, calculation work or next capability has been introduced.
