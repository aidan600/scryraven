# FAP / Author Boundary

Status: architecture doctrine only for future answer rendering.

Mode: BUILD.

## Purpose

This document records FinalAnswerPacket (FAP) and Author boundary doctrine for
future answer rendering. It is intended to keep future FAP inspection, source
gateway, and Author work aligned with the current RunKernel-owned answer path.

For the canonical multi-component producer, synthesis, validation, and
admission architecture, read
[MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).

## Core Doctrine

FAP is a constrained authority manifest, not a planner.

FAP packages upstream-authorized claims, required caveats, source bindings,
not-claimed boundaries, rendering references, and support posture references. It
does not create authority.

FAP may package admitted direct component material and admitted synthesis after
ordinary Sufficiency approves readiness. FAP must not generate, repair,
reinterpret, or validate synthesis, glue unadmitted component finals, or treat
graph admission alone as answer readiness.

The authority chain is:

```text
mode contract / query-class contract
-> planner / relation plan
-> Analyst evidence posture
-> SufficiencyReadiness
-> FAP packaging
-> Author rendering
```

FAP may carry:

- authorized claims;
- required caveats;
- optional or peripheral caveats only if externally labeled;
- source bindings;
- source-display requirements;
- not-claimed boundaries;
- mode/rendering refs;
- support posture refs.

FAP must not decide:

- what evidence means;
- which source is authoritative;
- which caveats matter;
- how much evidence is sufficient;
- what mode requires;
- what answer should be given if upstream authority is missing.

## Author Doctrine

Author is a constrained communication layer over FAP.

Author may optimize presentation. Author may not optimize truth.

Author may:

- choose clear wording;
- organize the answer;
- follow mode/rendering rules;
- include required caveats;
- surface source links readably;
- create a human-facing source gateway.
- explain synthesis that is already admitted and packaged by FAP.

Author must not:

- reinterpret evidence;
- resolve conflicts;
- decide source authority;
- drop required caveats;
- upgrade weak support;
- introduce new claims;
- infer missing context from model knowledge;
- change source posture.
- generate, repair, or validate synthesis, including glue between component
  outputs that upstream roles did not admit.

## Source Gateway Doctrine

Future answers should make claims inspectable through this chain:

```text
answer
-> claim/component
-> Analyst support posture
-> FAP authorization
-> source binding
-> source material
```

The source gateway is presentation and inspectability. It is not an alternate
evidence interpreter, source-authority engine, citation eligibility engine, or
source-obligation satisfaction path.

## Current Status

This document is doctrine only.

This phase does not modify FAP or Author behavior, implement source gateway UI,
redesign FAP, redesign Author, implement query planning, implement model
routing, run live validation, or change product behavior.

Product correctness remains unclaimed. ScryRaven is not friend-level MVP and is
not a general supported-query MVP.

Related current posture docs:

- [AG_FINAL_ANSWER_PACKET_HARDENING_01.md](AG_FINAL_ANSWER_PACKET_HARDENING_01.md)
- [AUTHOR_PROSE_ONLY_FINALIZATION_01.md](AUTHOR_PROSE_ONLY_FINALIZATION_01.md)
- [SOURCE_AUTHORITY_POSTURE.md](SOURCE_AUTHORITY_POSTURE.md)
- [RUN_CONTRACT_SEMANTIC_LOOP.md](RUN_CONTRACT_SEMANTIC_LOOP.md)
