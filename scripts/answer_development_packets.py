"""Freeze nine synthetic Answer-only development packets; never acquire or call models.

The evaluator obligations are written separately from model packets. Existing
artifacts are immutable: rerunning accepts identical bytes and rejects changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scryraven.sources import Evidence  # noqa: E402


def source(number: int, path: str, title: str, content: str) -> dict:
    return Evidence(
        id=f"E{number}",
        source_id=f"E{number}",
        url=f"https://example.test/answer-development/{path}",
        title=f"SYNTHETIC FIXTURE — {title}",
        content="SYNTHETIC FIXTURE: fictional entities and records for development.\n\n" + content,
    ).material()


def cases() -> list[dict]:
    return [
        {
            "id": "RICH_COMPARISON",
            "question": (
                "Compare Mara in Orchard Lane and Ellis in Rinkside as leaders. "
                "How do their principles, treatment of people and responses to failure "
                "shape what each gets done? Ground the comparison in concrete moments."
            ),
            "evidence": [
                source(1, "orchard-lane/episode-notes", "Orchard Lane episode notes", """Orchard Lane is a fictional ensemble comedy about neighbors maintaining a shared market. Mara owns a stall but holds no elected office. Neighbors ask her to settle disputes because she applies the same promises to friends and strangers. Her rule is that a deal accepted freely should be honored, but nobody owes a favor extracted by intimidation.

In 'The Spare Table', Mara's brother claims a late-arriving vendor's reserved table. Mara makes him return it and carries her own stock outside so both sellers can trade. She says little while doing the work. The solution protects the reservation but costs her a day's sales in the rain.

In 'The Lock', she refuses a landlord's demand that tenants provide unpaid weekend labor. She confronts him alone and wins a temporary reprieve. The other tenants subsequently complain that she made no plan for the next inspection and never asked what risks they could accept. Her consistency inspires trust; her instinct to absorb the conflict herself can leave others unprepared."""),
                source(2, "orchard-lane/finale-notes", "Orchard Lane finale notes", """In the Orchard Lane finale, 'Closing Time', Mara promises to repair every damaged stall before the market reopens. She runs out of time and conceals her exhaustion behind increasingly terse replies. When a younger vendor asks for one achievable task, Mara admits that she cannot complete the repairs alone. She divides the remaining jobs, accepts the vendor's different repair method and reopens only the safe half of the market.

Mara apologizes privately to the vendor she dismissed. Her warmth usually appears as practical help rather than speeches. At the reopening she still rejects a sponsor's demand to exclude a rival stall. The finale changes how she shares responsibility, without abandoning her existing rule of fair dealing."""),
                source(3, "rinkside/episode-notes", "Rinkside episode notes", """Rinkside is a fictional ensemble comedy about a struggling amateur hockey club. Ellis is the captain appointed by the coach. He believes commitment must be visible: attend practice, track back after mistakes and do unglamorous work for teammates. He uses loud jokes, blunt criticism and competitive drills to turn a collection of talented individuals into a team.

In 'One More Shift', star scorer Dean skips defensive drills and then blames a novice for an opposing goal. Ellis benches Dean despite needing his scoring. Later Ellis stays after practice with the novice, repeating the same drill until the novice can perform it. He praises the improvement in front of the team but calls Dean's excuse embarrassing in the same meeting.

In 'Bus Money', a teammate misses practice because a second job runs late. Ellis first mocks the absence. After learning the cause, he apologizes publicly and changes the schedule with the coach. He contributes to a travel fund without claiming credit. His standards remain demanding, but the episode distinguishes unwillingness to contribute from an obstacle a player cannot remove alone."""),
                source(4, "rinkside/finale-notes", "Rinkside finale notes", """In the Rinkside finale, 'Third Period', Ellis plays through an ankle injury because he thinks surrendering his place would betray the team. His slower skating leaves a gap and the team concedes twice. A substitute tells him that demanding sacrifice also means accepting replacement. Ellis sits out the last period and calls encouragement from the bench. The substitute scores once, but the club still loses the match.

After the loss Ellis names his own decision before discussing teammates' mistakes. He abandons his earlier boast that effort guarantees victory. The season ends with the players returning for voluntary practice. Their continued participation indicates shared commitment; the story does not give Ellis a championship or demonstrate that his abrasive methods suit every player."""),
            ],
            "obligations": [
                "Give an overall comparison of fair-dealing/community trust and explicit team standards/shared effort, not two disconnected summaries.",
                "Compare matched dimensions such as authority, communication, accountability and response to failure using concrete scene evidence.",
                "Preserve Mara's inflexible solitary burden and eventual delegation, alongside Ellis's demanding manner, practical care and public self-accountability.",
                "Distinguish Mara's successful partial reopening from Ellis's loss plus sustained team commitment; outcomes do not establish a universally superior leader.",
            ],
            "prohibited": [
                "Reduce Mara to kind and Ellis to cruel or to interchangeable tough leaders.",
                "Invent scenes, victories, audience consensus or real-world leadership effectiveness.",
            ],
        },
        {
            "id": "SIMPLE_LOOKUP_A",
            "question": "What time does the Cobalt Archive reading room close on Thursdays?",
            "evidence": [source(1, "cobalt-archive/hours", "Cobalt Archive opening hours", """Reading room: Monday to Wednesday 09:00–17:00; Thursday 09:00–18:00; Friday 09:00–16:00. The archive shop closes at 19:00 on Thursdays. These regular hours apply throughout September 2026.""")],
            "obligations": ["Answer 18:00 / 6 p.m. directly with the source citation.", "Keep the answer narrow; no headings, assumptions or background essay are needed."],
            "prohibited": ["Use the archive shop's 19:00 closing time for the reading room."],
        },
        {
            "id": "SIMPLE_LOOKUP_B",
            "question": "What is the return window for unopened Ridgefield tool kits bought online?",
            "evidence": [source(1, "ridgefield/returns", "Ridgefield online returns policy", """Unopened tool kits purchased through the Ridgefield online store may be returned within 30 calendar days after delivery. The purchase date does not start this window. Opened kits are excluded from this voluntary return policy. Separate procedures apply to damaged deliveries.""")],
            "obligations": ["Answer 30 calendar days after delivery with a citation.", "Preserve the clock's start point while staying concise."],
            "prohibited": ["Change delivery to purchase date or calendar days to business days.", "Develop unrelated damaged-item procedures or an assumptions section."],
        },
        {
            "id": "PARTIAL_EVIDENCE",
            "question": (
                "Why did the Riverton permit pilot speed up some applications but not others, "
                "and did it reduce end-to-end approval time overall?"
            ),
            "evidence": [
                source(1, "riverton/pilot-design", "Riverton permit pilot process note", """The fictional Riverton permit pilot ran from April through June 2026. It introduced a completeness check within one working day of submission, a single named case officer, and a shared queue for routine reviews. It did not change the external drainage board's review or the requirement to request a drainage opinion for applications in the flood corridor. Final approval still requires all applicable reviews to finish.

Under the former process, applicants often learned that a drawing was missing only after reaching the technical-review queue. The new completeness check returns such submissions before they enter that queue. A named officer can resolve questions across internal desks; that officer cannot sign off on behalf of the drainage board."""),
                source(2, "riverton/pilot-interim", "Riverton interim operational results", """The September 2026 interim note reports matched routine applications with complete drawings and no drainage-board referral. Their median internal review time fell from 12 working days in the prior comparison period to 5 working days in the pilot. Staff records attribute the largest queue reduction to early completeness checks and combined internal review assignments; the design was observational and did not isolate the separate causal contribution of either change.

Applications requiring drainage opinions still waited a median 24 working days for the board's response, compared with 23 in the prior period. Two pilot examples completed their internal checks in 4 and 6 working days but then waited for the required drainage opinion. Applicants with missing drawings were told earlier what to supply, although the time they took to submit corrected drawings varied."""),
                source(3, "riverton/pilot-reporting", "Riverton reporting scope note", """The published pilot tables report component processing times, not an end-to-end median for all submitted applications. At the reporting cutoff, some complex pilot applications were still open. The department has not yet published a comparable all-application submission-to-final-decision series including those cases. Routine internal-review medians must not be labeled the overall approval-time result. No claim of an overall increase or decrease is made in this interim note."""),
            ],
            "obligations": [
                "State that routine internal reviews became faster, while an overall end-to-end effect remains unestablished.",
                "Explain how early completeness checks and shared internal handling address internal queues, while the unchanged required external opinion remains a bottleneck.",
                "Use the 12-to-5-day routine result and roughly unchanged 23/24-day external wait with their actual populations and stages.",
                "Distinguish the plausible documented process mechanism from isolated causal proof; identify the missing comparable all-application completion series, including open complex cases.",
            ],
            "prohibited": ["Conclude overall approvals became faster by subtracting component medians.", "Let the missing aggregate result replace the supported explanation.", "Invent a quantitative causal split or require a broad unrelated research program."],
        },
        {
            "id": "USER_PREMISE_QUANT",
            "question": (
                "For this hypothetical only, our club holds 18 events. Each has 140 paying "
                "attendees at $12 each and 10 complimentary attendees. The venue costs $900 "
                "per event, and insurance is one $2,400 payment for the whole season. Ignore "
                "every other cost. What is the season's net surplus and the mean surplus per "
                "attendee, counting complimentary attendees? Round the per-attendee result to cents."
            ),
            "evidence": [],
            "obligations": [
                "Derive $30,240 revenue less $18,600 expenses = $11,640 seasonal surplus under the stated premises.",
                "Use 2,700 total attendances as denominator, including complimentary attendees, for $4.31 per attendance.",
                "Keep user_premises basis, no source readings/citations or added external costs; use calculator for material arithmetic.",
            ],
            "prohibited": ["Charge insurance once per event.", "Exclude complimentary attendance from denominator.", "Treat scenario figures as verified external results."],
        },
        {
            "id": "EVIDENCE_PLUS_CALCULATION",
            "question": (
                "For the two full years in these Ember Studio records, how much did the "
                "electricity bill fall in dollars and percent, and why did that percentage "
                "differ from the drop in electricity use? Include the standing charge."
            ),
            "evidence": [
                source(1, "ember-studio/2024-ledger", "Ember Studio 2024 electricity ledger", """This synthetic ledger covers the same Ember Studio premises and the entire calendar year 2024. Metered electricity consumption was 126,400 kWh. The uniform energy rate was $0.18 per kWh. The standing charge for the year was $2,400. These are the complete electricity charges for this comparison; no separate tax, credit or demand charge applies."""),
                source(2, "ember-studio/2025-ledger", "Ember Studio 2025 electricity ledger", """This synthetic ledger covers the same Ember Studio premises and the entire calendar year 2025. Metered electricity consumption was 102,200 kWh. The uniform energy rate was $0.20 per kWh. The standing charge for the year was $2,600. These are the complete electricity charges for this comparison; no separate tax, credit or demand charge applies. The ledger does not identify which operational changes caused consumption to fall."""),
            ],
            "obligations": [
                "Calculate complete annual bills of $25,152 and $23,040, a $2,112 reduction or about 8.40% of the earlier bill.",
                "Explain that consumption fell about 19.15%, while higher per-kWh price and standing charge offset part of the savings.",
                "Use deterministic calculator for material arithmetic and cite evidence for the external numeric inputs; results are derived, not new Evidence.",
            ],
            "prohibited": ["Omit standing charges or use later bill as reduction denominator.", "Attribute consumption changes to invented equipment upgrades or weather."],
        },
        {
            "id": "ASSUMPTION_POLICY",
            "question": (
                "I'm deciding how to explain a setup fee versus a per-use fee to our volunteers. "
                "Show when a reusable event sign would cost less than printing a new disposable "
                "sign for each event, with a small worked illustration. I have not picked "
                "products or prices yet."
            ),
            "evidence": [],
            "obligations": [
                "Explain a useful break-even relationship and provide a small numerical worked illustration by choosing conspicuously hypothetical inputs.",
                "Identify Answer-chosen inputs as arbitrary illustrative modeling assumptions, not user-provided prices, empirical estimates or external facts.",
                "Make the result explicitly conditional and readily overridable; separate the illustration from any actual purchasing conclusion.",
                "Under a promoted scenario contract, use scenario basis, empty readings/citations and calculator for material arithmetic. Under baseline contract, record whether desired illustration is impossible to represent honestly.",
            ],
            "prohibited": ["Claim that made-up prices are typical, current, researched or user-supplied.", "Give an empirical recommendation about unchosen products.", "Treat every missing price as requiring research before any useful illustration is possible."],
        },
        {
            "id": "ASSUMPTION_POLICY_NEGATIVE",
            "question": (
                "Which of Cedar Courier and Slate Courier would actually cost less for our "
                "next 1,000 deliveries under these quotes? We don't know their failed-delivery "
                "rates on our routes."
            ),
            "evidence": [
                source(1, "cedar-courier/quote", "Cedar Courier quote", """Synthetic quote for the specified batch of 1,000 first delivery attempts: base price is $4 per attempt. A failed first attempt adds one $9 recovery charge. That charge covers all subsequent handling for that parcel, with no additional attempt fees. This quote provides no measured or guaranteed first-attempt failure rate for the customer's routes."""),
                source(2, "slate-courier/quote", "Slate Courier quote", """Synthetic quote for the specified batch of 1,000 first delivery attempts: base price is $4.50 per attempt. A failed first attempt adds one $2 recovery charge. That charge covers all subsequent handling for that parcel, with no additional attempt fees. This quote provides no measured or guaranteed first-attempt failure rate for the customer's routes."""),
            ],
            "obligations": [
                "Leave the actual lower-cost provider unresolved because route-specific failure rates determine the outcome.",
                "Explain the base-price/recovery-charge trade-off with a compact symbolic relationship: Cedar = 4,000 + 9 F_C and Slate = 4,500 + 2 F_S, where F values are failed first attempts among 1,000 deliveries.",
                "Identify comparable route-specific first-attempt failure estimates or counts as the needed factual information; use evidence basis and citations for quote terms.",
                "A clearly bounded conditional threshold may illustrate the dependency, but must not introduce an arbitrary chosen rate and promote its winner as the actual answer.",
            ],
            "prohibited": ["Assume equal failure rates, zero failures or an invented typical rate to select the actual winner.", "Treat lower base price alone as total-cost superiority.", "Invent repeated retry charges contrary to the supplied one-time recovery terms."],
        },
        {
            "id": "CONFLICT_OR_APPLICABILITY",
            "question": (
                "For my standard Aster Workshop membership application received on 15 August "
                "2026 and approved on 2 October, is the fee $40 or $65? I never withdrew or "
                "resubmitted it. The newer help page says $65."
            ),
            "evidence": [
                source(1, "aster-workshop/fee-resolution", "Aster Workshop fee resolution, 2 June 2026", """The standard membership application fee increases from $40 to $65 for applications received on or after 1 September 2026. Applications received before that date retain the $40 fee even if review or approval occurs later. A withdrawn application followed by a new submission receives a new receipt date. This resolution concerns a fictional private workshop's membership process, not a government or legal fee."""),
                source(2, "aster-workshop/help", "Aster Workshop help page, updated 10 September 2026", """What does a standard membership application cost? The standard application fee is $65 from 1 September 2026. This help page summarizes fees for new applications. Transitional treatment of earlier submissions remains governed by the 2 June fee resolution; this update does not repeal that transition."""),
            ],
            "obligations": [
                "Answer $40 based on the stipulated 15 August receipt date and no withdrawal/resubmission.",
                "Explain that receipt date controls; October approval does not move the application into the new schedule.",
                "Resolve the apparent conflict by scope and retained transition, not recency or source counting; cite the controlling exception and relevant help-page scope.",
            ],
            "prohibited": ["Charge $65 because the help page is newer or approval occurred after 1 September.", "Describe the help page as repealing the explicit transition."],
        },
    ]


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def freeze(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise SystemExit(f"Refusing to change frozen artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def build(output: Path) -> dict:
    records = []
    obligations = []
    for case in cases():
        packet = {
            "question": case["question"],
            "conversation_context": [],
            "current_date": "2026-09-24",
            "phase": "answer",
            "evidence": case["evidence"],
            "acquisition_limitations": [],
            "budget": {
                "semantic_attempts": 0,
                "external_attempts": 0,
                "semantic_remaining": 12,
                "external_remaining": 16,
                "seconds_remaining": 300.0,
                "elapsed_seconds": 0.0,
            },
        }
        # Mirrors the deterministic baseline model's JSON logical packet identity.
        packet_sha256 = hashlib.sha256(
            json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        envelope = {
            "schema_version": 1,
            "packet_id": case["id"],
            "packet": packet,
            "acquisitions": case["evidence"],
            "provenance": {
                "synthetic": True,
                "origin": "Answer Development & Assumptions 01 synthetic fixture",
                "builder": "scripts/answer_development_packets.py",
                "public_data_declaration": "Wholly invented records and questions; no private, historical or acquired web material.",
                "use_status": "development",
                "packet_sha256": packet_sha256,
                "packet_sha256_encoding": "UTF-8 json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(',', ':'))",
            },
        }
        data = encoded(envelope)
        relative = f"packets/{case['id']}.json"
        freeze(output / relative, data)
        records.append({
            "packet_id": case["id"],
            "file": relative,
            "file_sha256": hashlib.sha256(data).hexdigest(),
            "packet_sha256": packet_sha256,
            "evidence_order": [item["id"] for item in case["evidence"]],
            "evidence_content_sha256": [
                hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
                for item in case["evidence"]
            ],
        })
        obligations.append({
            "packet_id": case["id"],
            "obligations": case["obligations"],
            "prohibited_mutations": case["prohibited"],
            "permitted_variation": ["Wording, concise structure and rounded presentation may vary while retaining material meaning."],
            "evaluation_questions": [
                "Does the answer resolve the task as far as warranted?",
                "Does a material omission weaken understanding or action?",
                "Could substantial prose be removed without useful loss?",
                "Are factual additions, assumptions, readings and citations honest?",
            ],
        })
    manifest = {"schema_version": 1, "synthetic": True, "packets": records}
    freeze(output / "packets" / "synthetic-manifest.json", encoded(manifest))
    freeze(output / "obligations" / "synthetic.json", encoded({
        "schema_version": 1,
        "notice": "Evaluator-only obligations. Never include in Answer model input.",
        "use_status": "development",
        "cases": obligations,
    }))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.output)
    print(json.dumps({"packets": len(manifest["packets"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
