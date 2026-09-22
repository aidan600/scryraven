"""Ordinary composition uses Exa Search plus LinkUp external Read."""

from core import linkup_transport
from core.exa_transport import DiscoveryCandidate, search_exa
from core.transport import FetchedMaterial
from scryraven.acquisition import AcquisitionLibrary


def test_ordinary_acquisition_uses_linkup_fetch_not_exa_contents():
    library = AcquisitionLibrary()
    assert library.fetch is linkup_transport.fetch_linkup
    assert library.search is search_exa


def test_linkup_read_failure_never_falls_back_to_exa_contents():
    calls = []

    def linkup_failure(url):
        calls.append(("linkup", url))
        raise RuntimeError("safe simulated failure")

    library = AcquisitionLibrary(fetch=linkup_failure)
    library.allow_question_urls("https://example.test/source")
    result = library.execute({"kind": "read", "target": "https://example.test/source"}, before_external=lambda: None)
    assert result["code"] == "read_failed"
    assert calls == [("linkup", "https://example.test/source")]


def test_search_remains_exa_and_read_uses_the_injected_linkup_fetch():
    calls = []
    url = "https://example.test/source"

    def exa_search(query):
        calls.append(("exa_search", query))
        return [DiscoveryCandidate("Source", url, "")]

    def linkup_fetch(requested_url):
        calls.append(("linkup_fetch", requested_url))
        return FetchedMaterial(requested_url, "Exact source material")

    library = AcquisitionLibrary(search=exa_search, fetch=linkup_fetch)
    assert library.execute({"kind": "search", "query": "source query"}, before_external=lambda: None)["status"] == "ok"
    assert library.execute({"kind": "read", "target": "C1"}, before_external=lambda: None)["new_acquisition_ids"] == ["E1"]
    assert calls == [("exa_search", "source query"), ("linkup_fetch", url)]


def test_repeated_full_read_and_find_are_local_after_linkup_acquisition():
    calls = []
    url = "https://example.test/source"
    library = AcquisitionLibrary(fetch=lambda requested_url: calls.append(requested_url) or FetchedMaterial(requested_url, "The threshold is 18 units."))
    library.allow_question_urls(url)
    assert library.execute({"kind": "read", "target": url}, before_external=lambda: None)["status"] == "ok"
    assert library.execute({"kind": "read", "target": url}, before_external=lambda: (_ for _ in ()).throw(AssertionError("unexpected refetch")))["local"]
    assert library.execute({"kind": "find", "query": "threshold"}, before_external=lambda: (_ for _ in ()).throw(AssertionError("unexpected external call")))["local"]
    assert calls == [url]
