"""CLI uses the ordinary two-contract runtime and real transport adapters offline."""
import json

import pytest
from test_model_transport import Response
from test_research_loop import answer, decision

from core import exa_transport, linkup_transport
from scryraven import __main__ as cli
from scryraven import model


def test_cli_ordinary_run_invokes_research_and_answer_over_real_exa_adapter(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    monkeypatch.setenv("EXA_API_KEY", "offline-test-value")
    outputs = iter([decision(), decision("answer", ["E1"]),
                    answer("The exact value is seven. [E1]") | {"source_readings": [
                        {"evidence_ref": "E1", "passages": ["The exact value is seven."]}
                    ]}])
    stages, providers = [], []

    def post(url, **kwargs):
        if url.endswith('/v1/responses'):
            stages.append(kwargs["json"]["text"]["format"]["name"])
            assert (kwargs["json"]["model"], kwargs["json"]["reasoning"]) == (
                ("gpt-6-luna", {"effort": "high"}) if stages[-1] == "research"
                else ("gpt-6-sol", {"effort": "medium"})
            )
            material = json.loads(''.join(b['text'] for b in kwargs['json']['input'][1]['content']))
            assert 'analysis' not in material and 'semantic_history' not in material
            if stages[-1] == 'answer':
                assert material['evidence'][0]['content'] == 'The exact value is seven.'
                assert 'working_understanding' not in material
            return Response({'status': 'completed', 'output': [{'type': 'message', 'phase': 'final_answer',
                             'content': [{'type': 'output_text', 'text': json.dumps(next(outputs))}]}]})
        providers.append(url)
        return Response({'results': [{'url': 'https://example.org/fact', 'title': 'Synthetic fact',
                                      'highlights': ['The exact value is seven.']}]})

    monkeypatch.setattr(model.requests, 'post', post)
    monkeypatch.setattr(exa_transport.requests, 'post', post)
    path = tmp_path / 'answer.html'
    assert cli.main(['What is the value?', '--trace-evidence', '--html', str(path)]) == 0
    captured = capsys.readouterr()
    assert stages == ['research', 'research', 'answer']
    assert len(providers) == 1 and providers[0].endswith('/search')
    assert 'The exact value is seven. [1]' in captured.out
    assert 'Status: Supported' in captured.out
    diagnostics = json.loads(captured.err)
    assert diagnostics['selected_evidence'][0]['content'] == 'The exact value is seven.'
    assert 'Synthetic fact' in path.read_text(encoding='utf-8')


def test_cli_ordinary_search_then_read_uses_linkup_not_exa_contents(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    monkeypatch.setenv("EXA_API_KEY", "offline-test-value")
    monkeypatch.setenv("LINKUP_API_KEY", "offline-test-value")
    outputs = iter([
        decision(),
        decision(requests=[{
            "kind": "read", "query": "", "target": "C1", "mode": "auto", "focus": "exact value",
            "scope": [], "start_char": None, "end_char": None,
        }]),
        decision("answer", ["E1"]),
        answer("The exact value is seven. [E1]") | {"source_readings": [
            {"evidence_ref": "E1", "passages": ["The exact value is seven."]}
        ]},
    ])
    providers = []

    def post(url, **kwargs):
        if url.endswith('/v1/responses'):
            return Response({'status': 'completed', 'output': [{'type': 'message', 'phase': 'final_answer',
                             'content': [{'type': 'output_text', 'text': json.dumps(next(outputs))}]}]})
        providers.append((url, kwargs.get("json")))
        if url == exa_transport.EXA_SEARCH_URL:
            return Response({'results': [{'url': 'https://example.org/fact', 'title': 'Synthetic fact'}]})
        if url == linkup_transport.LINKUP_FETCH_URL:
            return Response({'markdown': 'The exact value is seven.'})
        raise AssertionError(f"unexpected provider endpoint: {url}")

    monkeypatch.setattr(model.requests, 'post', post)
    monkeypatch.setattr(exa_transport.requests, 'post', post)
    monkeypatch.setattr(linkup_transport.requests, 'post', post)
    assert cli.main(['What is the value?', '--trace-evidence']) == 0
    captured = capsys.readouterr()
    assert providers == [
        (exa_transport.EXA_SEARCH_URL, {
            "query": "public fact", "type": "auto", "numResults": 6,
            "contents": {"text": False, "highlights": {"query": "public fact", "maxCharacters": 4000}},
        }),
        (linkup_transport.LINKUP_FETCH_URL, {"url": "https://example.org/fact"}),
    ]
    assert exa_transport.EXA_CONTENTS_URL not in str(providers)
    diagnostics = json.loads(captured.err)
    assert diagnostics['selected_evidence'][0]['content'] == 'The exact value is seven.'


def test_retired_architecture_selector_is_not_an_ordinary_cli_option():
    with pytest.raises(SystemExit) as caught:
        cli.main(['Question', '--v2'])
    assert caught.value.code == 2
