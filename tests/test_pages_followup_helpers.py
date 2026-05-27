from __future__ import annotations

from copy import deepcopy

from ui.pages_followup import (
    build_followup_assistant_message,
    build_followup_source_cards,
    followup_progress_label,
    render_followup_source_cards,
)
from ui.pages_thread import _source_chip_groups


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakeSt:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))

    def markdown(self, value: str) -> None:
        self.calls.append(("markdown", value))

    def write(self, value: str) -> None:
        self.calls.append(("write", value))

    def expander(self, label: str, expanded: bool = False) -> _Context:
        _ = expanded
        self.calls.append(("expander", label))
        return _Context()


def test_build_followup_source_cards_matches_sources_to_passage_metadata_by_url() -> None:
    synthesis_sources = {
        "https://second.example/report": {"id": 2, "title": "Second synthesis title"},
        "https://first.example/report": {"id": 1, "title": "First synthesis title"},
    }
    passages = [
        {
            "url": "https://first.example/report",
            "title": "First passage title",
            "domain": "first.example",
            "credibility": 3,
            "text": "First source preview text.",
        },
        {
            "url": "https://second.example/report",
            "title": "Second passage title",
            "domain": "second.example",
            "credibility": 2,
            "snippet": "Second source snippet.",
        },
    ]

    cards = build_followup_source_cards(synthesis_sources, passages)

    assert cards == [
        {
            "source_id": "1",
            "title": "First synthesis title",
            "domain": "first.example",
            "url": "https://first.example/report",
            "preview": "First source preview text.",
        },
        {
            "source_id": "2",
            "title": "Second synthesis title",
            "domain": "second.example",
            "url": "https://second.example/report",
            "preview": "Second source snippet.",
        },
    ]


def test_assistant_message_attaches_source_cards_without_mutating_content() -> None:
    content = "Answer with existing citation [1]."
    cards = [{"source_id": "1", "title": "Source", "domain": "example.com", "url": "https://example.com", "preview": ""}]

    message = build_followup_assistant_message(content=content, steps=[], source_cards=cards)

    assert message["content"] == content
    assert message["source_cards"] == cards


def test_old_assistant_message_without_source_cards_does_not_render_inferred_cards() -> None:
    old_message = {"role": "assistant", "content": "Old answer [1]."}
    st = _FakeSt()

    render_followup_source_cards(st, old_message.get("source_cards"))

    assert st.calls == []


def test_source_cards_missing_fields_degrade_safely() -> None:
    cards = build_followup_source_cards(
        {
            "": {},
            "https://bare.example/report": {"id": None},
        },
        [{"url": "https://bare.example/report"}],
    )

    assert cards == [
        {
            "source_id": "?",
            "title": "Untitled",
            "domain": "",
            "url": "",
            "preview": "",
        },
        {
            "source_id": "?",
            "title": "Untitled",
            "domain": "",
            "url": "https://bare.example/report",
            "preview": "",
        },
    ]


def test_followup_source_cards_omit_zero_missing_and_none_credibility() -> None:
    synthesis_sources = {
        "https://zero.example/report": {"id": 1, "title": "Zero score"},
        "https://none.example/report": {"id": 2, "title": "None score"},
        "https://missing.example/report": {"id": 3, "title": "Missing score"},
    }
    passages = [
        {
            "url": "https://zero.example/report",
            "domain": "zero.example",
            "credibility": 0,
            "text": "Zero score preview.",
        },
        {
            "url": "https://none.example/report",
            "domain": "none.example",
            "credibility": None,
            "text": "None score preview.",
        },
        {
            "url": "https://missing.example/report",
            "domain": "missing.example",
            "text": "Missing score preview.",
        },
    ]

    cards = build_followup_source_cards(synthesis_sources, passages)

    assert all("credibility" not in card for card in cards)

    st = _FakeSt()
    render_followup_source_cards(st, cards)

    captions = [value for kind, value in st.calls if kind == "caption"]
    assert "Credibility: 0" not in captions
    assert not any(value.startswith("Credibility:") for value in captions)


def test_followup_source_cards_omit_nonzero_credibility() -> None:
    synthesis_sources = {
        "https://positive.example/report": {"id": 1, "title": "Positive score"},
        "https://negative.example/report": {"id": 2, "title": "Negative score"},
    }
    passages = [
        {
            "url": "https://positive.example/report",
            "domain": "positive.example",
            "credibility": 3,
            "text": "Positive score preview.",
        },
        {
            "url": "https://negative.example/report",
            "domain": "negative.example",
            "credibility": -1,
            "text": "Negative score preview.",
        },
    ]

    cards = build_followup_source_cards(synthesis_sources, passages)

    assert all("credibility" not in card for card in cards)

    st = _FakeSt()
    render_followup_source_cards(st, cards)

    captions = [value for kind, value in st.calls if kind == "caption"]
    assert "Credibility: 3" not in captions
    assert "Credibility: -1" not in captions
    assert not any(value.startswith("Credibility:") for value in captions)


def test_thread_and_followup_public_helpers_omit_credibility_consistently() -> None:
    passages = [
        {
            "source_id": 1,
            "title": "Zero score",
            "domain": "zero.example",
            "credibility": 0,
            "url": "https://zero.example/report",
            "text": "Zero score preview.",
        },
        {
            "source_id": 2,
            "title": "Positive score",
            "domain": "positive.example",
            "credibility": 3,
            "url": "https://positive.example/report",
            "text": "Positive score preview.",
        },
        {
            "source_id": 3,
            "title": "Negative score",
            "domain": "negative.example",
            "credibility": -1,
            "url": "https://negative.example/report",
            "text": "Negative score preview.",
        },
    ]
    synthesis_sources = {
        passage["url"]: {"id": passage["source_id"], "title": passage["title"]}
        for passage in passages
    }

    groups = _source_chip_groups(passages)
    cards = build_followup_source_cards(synthesis_sources, passages)

    assert all("credibility" not in group for group in groups)
    assert all("credibility" not in card for card in cards)


def test_build_followup_source_cards_does_not_mutate_inputs() -> None:
    synthesis_sources = {"https://example.com/a": {"id": 1, "title": "A"}}
    passages = [{"url": "https://example.com/a", "title": "Passage A", "text": "Preview"}]
    sources_before = deepcopy(synthesis_sources)
    passages_before = deepcopy(passages)

    build_followup_source_cards(synthesis_sources, passages)

    assert synthesis_sources == sources_before
    assert passages == passages_before


def test_render_followup_source_cards_renders_when_present() -> None:
    st = _FakeSt()

    render_followup_source_cards(
        st,
        [
            {
                "source_id": "1",
                "title": "Source Title",
                "domain": "example.com",
                "url": "https://example.com/a",
                "preview": "Preview text.",
                "credibility": "3",
            }
        ],
    )

    assert ("caption", "Sources") in st.calls
    assert ("expander", "[1] example.com") in st.calls
    assert ("markdown", "**Source Title**") in st.calls
    assert ("write", "Preview text.") in st.calls
    assert ("caption", "Credibility: 3") not in st.calls
    assert not any(
        value.startswith("Credibility:")
        for kind, value in st.calls
        if kind == "caption"
    )


def test_followup_progress_label_maps_internal_copy_and_preserves_unknown_labels() -> None:
    assert followup_progress_label("Checking follow-up search need...") == "Reviewing thread context..."
    assert followup_progress_label("Existing context sufficient; skipping web search.") == "Using saved context..."
    assert followup_progress_label("Existing context sufficient.") == "Using saved context."
    assert followup_progress_label("Searching the web: ['query']") == "Searching the web: ['query']"
