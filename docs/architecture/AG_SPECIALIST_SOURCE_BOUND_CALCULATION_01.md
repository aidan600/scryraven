# AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01

Status: completed implementation posture for the first useful Specialist MVP.

Proof class: `component_harness_proof`.

Product path affected: RunKernel-reduced Specialist source-bound calculation
state over already custodied/admitted/source-bound numeric inputs. No live
provider, broker, retrieval, fetch/read, model, ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, source-obligation satisfaction,
`current_answer_contract` mutation, or product correctness path is opened.

## Result

`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` introduces Specialist as
source-bound deterministic calculation only. Specialist is not product
authority. It records whether already source-bound numeric inputs can support a
small deterministic calculation, and it preserves exact input lineage, formula
lineage, units, assumptions, caveats, blockers, and closed downstream flags.

RunKernel owns Specialist calculation reduction. The canonical state is a
RunKernel-reduced Specialist calculation record/projection/history under
`specialist_source_bound_calculation`. The helper can build a record from
fixture source-bound numeric inputs, but canonical Specialist state comes only
from RunKernel authorization and reduction.

## Calculation Behavior

Supported deterministic operators are:

- `sum`
- `difference`
- `product`
- `ratio`
- `percentage`
- `percentage_point_difference`
- `simple_rate`
- `weighted_average`

Inputs must be source-bound and lineage-preserving. Each numeric input carries a
typed numeric value, unit, label, component id, input digest, currentness/source
class posture, caveats, and source/custody/content/SemanticObservation/Analyst
refs when available. Weighted-average weights must be source-bound or explicitly
fixture-bound.

Invalid, stale, contradictory, mixed-unit, missing-unit, missing-lineage,
non-numeric, denominator-zero, or unsupported-formula calculations remain
blocked, invalid_input, or contested; in short, unsafe calculations remain
blocked or contested rather than becoming support. Specialist does not infer
missing values, normalize incompatible units without explicit inputs, parse
arbitrary formulas, execute arbitrary code, or calculate from raw/unbounded
text.

## Boundaries

Specialist calculation output does not decide ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author input, citation eligibility, source-obligation
satisfaction, current-answer-contract mutation, or product correctness.
ComponentCoverage remains the canonical component support reducer.
Sufficiency/FAP/Author remain closed.

Scrutineer can review Specialist calculation posture and refs enough to flag
unsupported calculation, stale input, contradiction, or missing source-bound
lineage. Scrutineer does not calculate or authorize Specialist output.

Existing Economist surfaces remain legacy/passive unless deliberately reused
without authority revival. This phase does not revive legacy Economist handoff
authority, Author behavior, citation behavior, or old orchestration paths.

The next likely phase is `AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01`.
