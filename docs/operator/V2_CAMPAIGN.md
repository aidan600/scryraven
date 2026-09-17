# V2 development campaign

This is the frozen development manifest for the coherent V2 implementation work
item, frozen on 2026-09-17 before its first campaign submission. Questions and
outcome rubrics are fixed; queries, sources, identities, trajectories, and source
counts are not prescribed. All cases are development evidence, never held-out
proof. Only each selected question is supplied to the product runtime. Rubrics
and case labels remain outside model inputs.

The manifest SHA-256 is recorded below. It hashes the manifest JSON serialized
with UTF-8, sorted keys, compact separators, and unescaped Unicode, without a
trailing newline. Wording changes require a new manifest rather than silently
reclassifying the existing campaign.

Manifest SHA-256: `bdcc3c1c7b09b00c8b7dadf45573f5d0d7636b31f7272b792c1ee2d3d27f7e0c`

<!-- v2-campaign-manifest:start -->
```json
{
  "schema_version": 1,
  "campaign_id": "v2-adaptive-research-01",
  "frozen_date": "2026-09-17",
  "use_status": "development",
  "cases": [
    {
      "id": "F01",
      "class": "simple_authoritative_fact",
      "question": "According to the BIPM, which four SI prefixes were added in 2022, and what are their symbols and powers of ten?",
      "follows": null,
      "rubric": [
        "Answer the requested prefix names, case-sensitive symbols, and powers from applicable authoritative material.",
        "Resolve exact valid citations to the material supplied for answering.",
        "Stop promptly once the narrow factual operation is established."
      ]
    },
    {
      "id": "F02",
      "class": "retained_evidence_followup",
      "question": "Which two of those represent factors smaller than one, and how do their magnitudes compare?",
      "follows": "F01",
      "rubric": [
        "Resolve the conversation referent while keeping prior generated answers distinct from Evidence.",
        "Freshly interpret actual retained Evidence and support the requested magnitude comparison.",
        "Demonstrate useful retained-material reuse without unnecessary external acquisition."
      ]
    },
    {
      "id": "F03",
      "class": "current_rule_material_exception",
      "question": "Under the current parkrun rules, when may a child under 11 participate in a 5k parkrun or a junior parkrun without an adult staying within arm’s reach? Explain the age limits and any material exceptions.",
      "follows": null,
      "rubric": [
        "Establish applicable current governing rules and distinguish the 5k and junior event scopes.",
        "Preserve material age limits, supervision requirements, conditions, and exceptions.",
        "Do not replace a qualified permission or requirement with an unconditional statement."
      ]
    },
    {
      "id": "F04",
      "class": "future_actual_not_observable",
      "question": "What was the British Museum’s total number of visitors during calendar year 2027?",
      "follows": null,
      "rubric": [
        "Recognize that the requested calendar year has not completed at the supplied current date.",
        "Distinguish actual completed-period totals from forecasts, earlier years, and financial-year reporting.",
        "Return a useful honest limitation promptly; repeated searches and budget exhaustion do not establish nonexistence."
      ]
    },
    {
      "id": "F05",
      "class": "technical_multisource_explanation",
      "question": "How do HTTP cache validation with ETag/If-None-Match and Last-Modified/If-Modified-Since differ, and how does Cache-Control: no-cache affect their use? Ground the explanation in the governing HTTP specifications.",
      "follows": null,
      "rubric": [
        "Use applicable governing specifications for the attributed technical relationships.",
        "Explain validator differences and their interaction with no-cache, preserving material conditions and precedence.",
        "Build the explanatory relationship from supplied premises without inventing connective rules."
      ]
    },
    {
      "id": "F06",
      "class": "specific_event_version_reception",
      "question": "How did players receive Path of Exile 2’s The Third Edict update during its first month after release? Distinguish reactions to this update from reactions to the game overall, and describe the limits of the available evidence.",
      "follows": null,
      "rubric": [
        "Establish the requested version and observation period before interpreting reception.",
        "Use meaningful post-release reactions applicable to this update; distinguish previews, promotion, and activity measures from reception.",
        "Preserve conflicting reactions and qualify sample breadth instead of asserting unsupported population frequencies."
      ]
    },
    {
      "id": "F07",
      "class": "recursive_identity_qualifications",
      "question": "What are the qualifications of the new executive director of St. Dorothy’s Rest?",
      "follows": null,
      "rubric": [
        "Preserve the person-focused request while investigating applicable identity and appointment chronology.",
        "Treat plausible candidates as disposable and follow reasonably obtainable consequential evidence.",
        "Establish the applicable appointee if reasonably obtainable, then research that person’s qualifications; role requirements may supply comparison context.",
        "An honest cautious answer does not excuse failure to pursue obtainable decisive evidence."
      ]
    },
    {
      "id": "F08",
      "class": "multicomponent_revised_structure",
      "question": "What did the original LK-99 reports claim, what did subsequent replication actually establish, and does the later evidence justify calling LK-99 a room-temperature, ambient-pressure superconductor?",
      "follows": null,
      "rubric": [
        "Distinguish the original claims, later replication observations, and the inference justified by those observations.",
        "Revise the organizing interpretation when later evidence changes the problem, including material sample or measurement distinctions.",
        "Synthesize applicable supplied sources while preserving uncertainty and separating demonstrated findings from generalization."
      ]
    }
  ]
}
```
<!-- v2-campaign-manifest:end -->

## Execution and review

Use `scripts/v2_campaign.py` through the existing credential broker. It invokes
ordinary `ResearchSession.ask` with the V2 engine and explicit GPT-5.6 Luna /
medium configuration. The runner records normalized public observations and
results as JSON lines on stdout for broker sanitation. It does not acquire
sources, choose routes, edit prompts, seed Evidence, or judge answers itself.

Select one case with `--case F03 --revision <tested-head>`. For an ephemeral
retained sequence select `--case F01 --case F02`; these are two submissions. An
external `--database` creates a durable session, and `--resume <session-id>`
with that database runs F02 after the exact F01 question. Other cases start fresh.
The runner never automatically retries a failed submission.

Start with `--semantic-attempts 12 --external-attempts 16 --seconds 120`.
The work-item maxima are 20 semantic attempts, 24 external attempts, 300 seconds
per submission, and 50 top-level submissions in total. The runner checks the
per-submission maxima; the controlling agent maintains the whole-work-item
submission ledger, including CLI smoke runs, failures, follow-ups and reruns.
No automatic quota consumption or subsequent phase is implied.

Campaign judgment requires reviewing the answer, exact actual acquisitions,
exact exposure, and compact decisions to locate the first consequential loss.
Review intent, applicability, support, attention, recursion, stopping, economy,
final-packet selection, final answer, and citation custody separately. A useful
answer is not proof of every dimension; a partial result is not automatically a
failure. Failed searches and exhausted budgets never prove nonexistence.

After a substantive failure, diagnose and make a reasoned general correction
with relevant offline checks before another live execution. Unchanged-code
repetition requires a recorded variability or transient-failure rationale.

Keep useful sanitized exact evidence under ignored `local-evals/`, following
`LOCAL_EVALUATION_CORPUS.md`. Preserve questions, actual Evidence, structured
public decisions, answers, safe counters and provenance. Do not capture `.env`,
credentials, raw provider payloads, hidden reasoning, full prompt dumps,
unrelated private logs, or session databases in the evaluation corpus.
