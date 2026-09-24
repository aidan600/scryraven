"""Answer Evidence presentation keeps exact material and the existing contract."""

import hashlib
import json
from copy import deepcopy

from scryraven.model import OpenAIModel
from scryraven.research import AnswerDecision


class Response:
    def __init__(self, reply):
        self.reply = reply

    def raise_for_status(self):
        pass

    def json(self):
        return {"status": "completed", "output": [
            {"type": "message", "phase": "final_answer", "content": [
                {"type": "output_text", "text": self.reply},
            ]},
        ]}


def _user_json(payload):
    return "".join(block["text"] for block in payload["input"][1]["content"])


def test_answer_evidence_identity_before_body_is_lossless_and_deterministic(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    body = 'Exact source: 17,325–18,920 lb.\r\n"Quoted" 🦉'
    first = {
        "content": body, "z_future": {"nested": [3, None, "one"]},
        "end_char": 81, "source_id": "S1", "id": "E1", "title": "GE Passport",
        "acquisition": {"type": "search", "provider": "exa"},
        "url": "https://example.test/passport", "parent_id": None,
        "start_char": 0, "a_future": [None, {"qualifier": "retained"}],
    }
    second = {"content": "Second exact body\n", "id": "E2", "source_id": "S2",
              "parent_id": "E1", "start_char": 4, "end_char": 22, "url": None}
    material = {"z_future": "tail", "evidence": [first, second],
                "question": "What is the range?", "phase": "answer",
                "a_future": {"present": None}}
    original = deepcopy(material)
    packets = []
    model = OpenAIModel(post=lambda _url, **kwargs: (
        packets.append(kwargs["json"]) or Response('{}')
    ))

    model("answer", "instructions", material, AnswerDecision.model_json_schema())
    raw = _user_json(packets[0])
    parsed = json.loads(raw)
    legacy_parsed = json.loads(json.dumps(original, ensure_ascii=False, sort_keys=True))
    assert material == original
    assert parsed == legacy_parsed == original
    assert len(parsed["evidence"]) == len(original["evidence"]) == 2
    assert [item["id"] for item in parsed["evidence"]] == ["E1", "E2"]
    assert list(parsed) == ["phase", "question", "a_future", "evidence", "z_future"]
    assert list(parsed["evidence"][0]) == [
        "id", "source_id", "acquisition", "title", "url", "parent_id",
        "start_char", "end_char", "a_future", "z_future", "content",
    ]
    assert list(parsed["evidence"][1]) == [
        "id", "source_id", "url", "parent_id", "start_char", "end_char", "content",
    ]
    for before, after in zip(original["evidence"], parsed["evidence"], strict=True):
        for key in ("id", "source_id", "acquisition", "title", "url",
                    "parent_id", "start_char", "end_char", "a_future", "z_future"):
            assert after.get(key) == before.get(key)
            assert (key in after) == (key in before)
        assert hashlib.sha256(after["content"].encode("utf-8")).hexdigest() == (
            hashlib.sha256(before["content"].encode("utf-8")).hexdigest()
        )
        assert len(after["content"]) == len(before["content"])
        assert after["content"].encode("utf-8") == before["content"].encode("utf-8")

    reordered = dict(reversed(list(deepcopy(material).items())))
    reordered["evidence"] = [dict(reversed(list(item.items())))
                             for item in reordered["evidence"]]
    model("answer", "instructions", reordered, AnswerDecision.model_json_schema())
    assert _user_json(packets[1]) == raw
    assert packets[0]["text"]["format"]["schema"] == AnswerDecision.model_json_schema()


def test_answer_top_level_bytes_and_breakpoints_change_only_inside_evidence(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    body = "Unchanged exact body"
    evidence = [{"content": body, "id": "E1"}]
    history = [{"question": "Earlier?", "answer": "Earlier answer."}]
    material = {
        "output_correction": None, "z_future": 7, "evidence": evidence,
        "question": "Current?", "phase": "answer", "current_date": "2026-09-24",
        "conversation_context": history, "a_future": 3,
    }
    packets = []
    model = OpenAIModel(post=lambda _url, **kwargs: (
        packets.append(kwargs["json"]) or Response('{}')
    ))
    model("answer", "instructions", material, AnswerDecision.model_json_schema())
    payload = packets[0]
    blocks = payload["input"][1]["content"]
    raw = _user_json(payload)
    new_item = '{"id": "E1", "content": "Unchanged exact body"}'
    old_item = json.dumps(evidence[0], ensure_ascii=False, sort_keys=True)
    legacy_top_level = (
        '{"conversation_context": ' + json.dumps(history, ensure_ascii=False, sort_keys=True)
        + ', "current_date": "2026-09-24", "phase": "answer", "question": "Current?"'
        + ', "a_future": 3, "evidence": [' + old_item
        + '], "z_future": 7, "output_correction": null}'
    )
    assert raw.replace(new_item, old_item) == legacy_top_level
    assert list(json.loads(raw)) == [
        "conversation_context", "current_date", "phase", "question",
        "a_future", "evidence", "z_future", "output_correction",
    ]
    assert len(blocks) == 2
    assert blocks[0]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert "prompt_cache_breakpoint" not in blocks[1]


def test_research_layout_unchanged_and_answer_validator_accepts_same_source_reading(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    body = "An acquired fact."
    decision = {"source_readings": [{"evidence_ref": "E1", "passages": [body]}],
                "posture": "supported", "support_basis": "evidence",
                "answer": "An acquired fact. [E1]", "missing_information": None}
    packets = []
    model = OpenAIModel(post=lambda _url, **kwargs: (
        packets.append(kwargs["json"]) or Response(json.dumps(decision))
    ))
    research_material = {"phase": "research", "question": "Q",
                         "evidence": [{"content": body, "id": "E1"}],
                         "working_understanding": None}
    model("research", "instructions", research_material, {})
    research_blocks = packets[0]["input"][1]["content"]
    assert research_blocks == [
        {"type": "input_text", "text": '{"phase": "research", "question": "Q"',
         "prompt_cache_breakpoint": {"mode": "explicit"}},
        {"type": "input_text", "text": ', "working_understanding": null, '
         '"evidence": [{"id": "E1", "content": "An acquired fact."}]}'},
    ]
    answer_material = {"phase": "answer", "question": "Q",
                       "evidence": [{"content": body, "id": "E1"}]}
    raw_decision = model("answer", "instructions", answer_material,
                         AnswerDecision.model_json_schema())
    assert json.loads(_user_json(packets[1])) == answer_material
    assert AnswerDecision.model_validate_json(raw_decision).model_dump() == decision
    assert packets[1]["text"]["format"]["schema"] == AnswerDecision.model_json_schema()
