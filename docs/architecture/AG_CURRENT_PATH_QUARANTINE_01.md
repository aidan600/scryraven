# Current-Path Classification Contract

Status: supporting
Authority: routed-support
Default-read: no

## Responsibility

This document owns narrow classification vocabulary for describing repository
surfaces without inflating passive, fixture, harness, or historical material
into current product authority.

It is not an installed-state registry or a roadmap. Route temporal questions
to:

- [ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md) for installed behavior,
  supported envelope, not-installed items, and explicit nonproofs;
- [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) for priority and phase
  sequence; and
- [Proof Class and Actual App Delta Gate](../codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md)
  for proof class, product delta, consumer seam, harness, and nonproof rules.

Concern-specific architecture contracts own durable responsibilities and
invariants. Code and focused tests remain executable authority. This supporting
vocabulary must not override either.

## Classification Vocabulary

| Classification | Meaning |
| --- | --- |
| current product-consumed | The ordinary CLI/app/product path consumes the behavior through a named runtime consumer. |
| current internal authority | A current named authority such as RunKernel owns or reduces the state, but ordinary product consumption must still be established separately. |
| supporting/passive | A useful helper, projection, packet, document, adapter, or record that does not itself decide canonical authority. This includes the older phrase `current passive/supporting projection`. |
| fixture-only | A test fixture proves a bounded seam without proving ordinary product execution or live behavior. |
| offline harness | An executable offline scaffold or diagnostic path. It is not product-consumed unless the ordinary path actually consumes it. |
| integration-staging | A temporary scaffold while wiring a named ordinary consumer, with an explicit integration deadline and exit condition. |
| product-facing dry run | Human-reviewable product-shaped output from bounded offline inputs. It is not live correctness or broad product quality. |
| historical/proof-only | Retained chronology or proof material that must not be cited as current product progress. |
| legacy | Compatibility or superseded machinery retained without current authority. Reuse requires an explicit current owner and consumer. |
| closed unless licensed | A high-custody surface that a phase may not inspect or change without exact authority, scope, and validation permission. |

Use `current product-consumed` only when the phase can name the ordinary
entrypoint, runtime consumer, and affected product output. A surface can be
current internal authority while its available evidence remains fixture-only,
offline-harness, or product-facing-dry-run proof.

## Classification Rules

- A dataclass, trace key, projection, packet, prompt instruction, or test
  fixture does not establish runtime consumption.
- A worker proposal does not establish RunKernel admission.
- Search candidates are not evidence; readable content is not semantic
  support; custody is not component satisfaction.
- ComponentCoverage is not readiness; graph admission is not FAP packaging;
  FAP packaging is not Author rendering.
- Human-readable output is not live or product correctness by itself.
- A surface with no current consumer is supporting/passive, fixture-only,
  offline-harness, historical/proof-only, legacy, or closed—not implicitly
  current product-consumed.
- Old paths retained for compatibility or history must not be revived by prose.
  Reuse or replacement requires a named owner, consumer, guard, and old-path
  treatment.
- Provider/model/search/fetch/read/retrieval, prompts, private data, citation
  behavior, source-obligation satisfaction, and Author behavior remain closed
  unless a phase explicitly licenses the exact surface.

## Proof And Harness Routing

Proof-class claims and harness expiration rules belong to the
[Proof Class and Actual App Delta Gate](../codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md).
At minimum, a non-product scaffold must name its harness label, ordinary path
guarded or fed, runtime consumer, integration deadline, exit condition, why it
is not a shadow product path, and forbidden interpretation.

Passing a docs/static guard proves repository posture only. It does not prove
runtime behavior, live acquisition, citation behavior, answer quality, or
product correctness.

## Non-Authority

This contract intentionally contains no broad product-state registry, phase
chronology, active next gate, or roadmap recommendation. Installed surfaces
must not be called legacy merely because an older quarantine record predates
their ordinary activation.
