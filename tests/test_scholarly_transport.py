"""Offline checks for the Europe PMC wire format and publication identity."""

import json
import threading

import pytest
import requests
from pydantic import ValidationError

from core.scholarly_transport import (
    EUROPE_PMC_API,
    JUFO_SEARCH_URL,
    SCHOLARLY_FAILURE_CODES,
    VENUE_FAILURE_CODES,
    PublicationMetadata,
    ScholarlyTransportError,
    VenueStanding,
    VenueTransportError,
    fetch_scholarly,
    lookup_venue,
    search_scholarly,
)


class Response:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *errors):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("raw response detail", response=self)

    def iter_content(self, chunk_size):
        yield self.content


def test_selects_original_abstracts_and_keeps_preprint_and_article_distinct():
    article = {
        "source": "MED", "pmid": "29000001", "pmcid": "PMC100001",
        "doi": "10.1234/Article", "title": "Heat response <i>in vitro</i>",
        "authorList": {"author": [{"fullName": "Susan Reed"}, {"collectiveName": "Cell Consortium"}]},
        "abstractText": "<h4>METHODS</h4>Sixty cultures with a sham treatment. "
                        "<h4>RESULTS</h4>ATP&lt;3 nM; n=10<sup>4</sup> cells; 95% CI 1.8–2.4 nM.",
        "pubYear": "2018", "pubTypeList": {"pubType": ["Journal Article"]},
        "journalInfo": {"journal": {"title": "Cell Stress Methods", "issn": "2042-0021", "essn": "2042-0021"}},
        "subsetList": {"subset": [{"code": "IM", "name": "Index Medicus"}]},
        "isOpenAccess": "Y", "inEPMC": "Y", "license": "cc by",
        "fullTextUrlList": {"fullTextUrl": [
            {"site": "Unpaywall", "availabilityCode": "OA", "documentStyle": "html",
             "url": "https://repository.example.org/article-100001"},
        ]},
    }
    preprint = {
        "source": "PPR", "id": "PPR100001", "doi": "10.1101/preprint", "title": "Heat response",
        "bookOrReportDetails": {"publisher": "bioRxiv"},
        "pubTypeList": {"pubType": ["Preprint"]},
        "commentCorrectionList": {"commentCorrection": [
            {"type": "Preprint of", "source": "MED", "id": "29000001",
             "note": "Link created based on a title-first author match"},
        ]},
    }
    duplicate = {**article, "pmid": "29000002", "pmcid": "PMC100002", "doi": "10.1234/ARTICLE"}
    dispatched = []

    def get(url, **kwargs):
        assert dispatched == ["heat stress AND ATP"]
        assert url == f"{EUROPE_PMC_API}/search"
        assert kwargs["params"] == {
            "query": "heat stress AND ATP", "format": "json", "resultType": "core", "pageSize": 8,
        }
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        return Response(json.dumps({"resultList": {"result": [article, preprint, duplicate]}}).encode())

    published, posted = search_scholarly("heat stress AND ATP", get=get, on_dispatch=dispatched.append)
    assert published.url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC100001/"
    assert published.full_text_pmcid == "PMC100001"
    assert published.title == "Heat response in vitro"
    assert published.abstract == (
        "METHODS\nSixty cultures with a sham treatment.\nRESULTS\n"
        "ATP<3 nM; n=10^{4} cells; 95% CI 1.8–2.4 nM."
    )
    assert published.publication.open_article_available
    assert published.publication.doi == "10.1234/article"
    assert published.publication.authors == ("Susan Reed", "Cell Consortium")
    assert published.publication.issns == ("2042-0021",)
    assert published.publication.status == "published"
    assert published.publication.indexing.source == "NLM Index Medicus"
    assert published.publication.year == 2018
    assert published.publication.open_access_url == "https://repository.example.org/article-100001"
    assert posted.abstract == ""
    assert posted.publication.status == "preprint" and posted.publication.indexing is None
    assert posted.publication.journal == "bioRxiv"
    assert posted.publication.related[0].kind == "published_version"
    assert posted.publication.related[0].url == "https://pubmed.ncbi.nlm.nih.gov/29000001/"
    assert posted.publication.related[0].note == "Link created based on a title-first author match"
    snapshot = published.publication.model_dump(mode="json", exclude_none=True)
    assert PublicationMetadata.model_validate(snapshot) == published.publication
    assert "Sixty cultures" not in json.dumps(snapshot)


def test_recognizes_positive_notice_but_not_subscription_or_pubmed_membership():
    restricted = {
        "source": "MED", "pmid": "32100012", "pmcid": "PMC100005", "doi": "10.1234/other",
        "isOpenAccess": "N", "inEPMC": "Y", "title": "Original dose study",
        "abstractText": "Measured median drug concentration.",
        "commentCorrectionList": {"commentCorrection": [
            {"source": "MED", "id": "32300013", "type": "Erratum in"},
            {"source": "MED", "id": "32100011", "type": "Retraction in"},
            {"source": "MED", "id": "32100010", "type": "Comment in"},
        ]},
        "fullTextUrlList": {"fullTextUrl": [
            {"site": "Europe_PMC", "availabilityCode": "F", "url": "https://europepmc.org/articles/PMC100005"},
            {"site": "Publisher", "availabilityCode": "S", "url": "https://publisher.example/restricted"},
        ]},
    }
    records = [restricted, {
        **restricted, "isOpenAccess": "Y", "pmid": "32100014", "pmcid": "PMC100006",
        "doi": "10.1234/no-license-hint", "commentCorrectionList": {},
    }]
    first, second = search_scholarly("dose", get=lambda *_a, **_kw: Response(
        json.dumps({"resultList": {"result": records}}).encode(),
    ))
    assert first.full_text_pmcid is None
    assert first.publication.open_access_url is None
    assert first.publication.indexing is None
    assert first.publication.status == "retracted"
    assert [relation.kind for relation in first.publication.related] == ["correction", "retraction"]
    assert first.url == "https://doi.org/10.1234/other"
    assert second.full_text_pmcid == "PMC100006"
    assert second.publication.status is None


JATS = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article SYSTEM "JATS-archivearticle1.dtd">
<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article">
  <front>
    <article-meta>
      <article-id pub-id-type="pmcid">PMC100001</article-id>
      <article-id pub-id-type="manuscript">NIHMS12345</article-id>
      <abstract><p>Cell <i>stress</i> response.</p></abstract>
      <permissions><license><license-p>See <ext-link
        xlink:href="http://creativecommons.org/licenses/by/4.0/">CC BY</ext-link></license-p>
      </license></permissions>
    </article-meta>
  </front>
  <body>
    <sec><title>Methods</title><p>Sixty cultures; assay at 42 &#xB0;C.</p></sec>
    <sec><title>Results</title><p>ATP persisted for &gt;6 hours.</p></sec>
  </body>
  <back><sec><title>Limitations</title><p>One cell line.</p></sec></back>
</article>"""


def test_fixed_origin_oa_read_preserves_exact_readable_text_and_its_limits():
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return Response(JATS)

    acquired = fetch_scholarly("PMC100001", get=get)
    assert calls == [f"{EUROPE_PMC_API}/PMC100001/fullTextXML"]
    assert acquired.url == "https://pmc.ncbi.nlm.nih.gov/articles/PMC100001/"
    assert acquired.content == (
        "Cell stress response.\n\nMethods\nSixty cultures; assay at 42 °C.\nResults\n"
        "ATP persisted for >6 hours.\n\nLimitations\nOne cell line."
    )
    assert acquired.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert acquired.version == "author_manuscript"


def test_oa_read_does_not_flatten_powers_or_math_alternatives():
    formulas = (
        b"With 10<sup>6</sup> cells at 5% CO<sub>2</sub> and "
        b"<alternatives><math><mfrac><mi>a</mi><mi>b</mi></mfrac></math>"
        b"<tex-math>a/b</tex-math></alternatives> as the ratio."
    )
    xml = JATS.replace(b"Sixty cultures; assay at 42 &#xB0;C.", formulas)
    article = fetch_scholarly("PMC100001", get=lambda *_args, **_kwargs: Response(xml))
    assert "With 10^{6} cells at 5% CO_{2} and a/b as the ratio." in article.content
    assert "mfrac" not in article.content


@pytest.mark.parametrize(("response", "code"), [
    (Response(JATS.replace(b"PMC100001", b"PMC888888")), "europe_pmc_identity_mismatch"),
    (Response(JATS.replace(b"/by/", b"/by-nc/")), "europe_pmc_license_unavailable"),
    (Response(JATS.replace(b'DOCTYPE article SYSTEM "JATS-archivearticle1.dtd"',
                          b'DOCTYPE article [<!ENTITY term "content">]')), "europe_pmc_xml_invalid"),
    (Response(b"<html>access denied</html>"), "europe_pmc_material_unavailable"),
    (Response(b"", 302), "europe_pmc_endpoint_redirected"),
    (Response(b"", 429), "europe_pmc_rate_limited"),
])
def test_unsafe_or_unavailable_article_never_supplies_evidence(response, code):
    assert code in SCHOLARLY_FAILURE_CODES
    with pytest.raises(ScholarlyTransportError, match=f"^{code}$"):
        fetch_scholarly("PMC100001", get=lambda *_args, **_kwargs: response)


def test_get_rejects_unobserved_url_shaped_identifier_before_dispatch():
    with pytest.raises(ValueError, match="PubMed Central identifier"):
        fetch_scholarly("PMC100001/../../", get=lambda *_a, **_kw: pytest.fail("unexpected dispatch"))


def test_publication_link_validation_rejects_unsafe_schemes():
    with pytest.raises(ValidationError):
        PublicationMetadata(related=[{"kind": "correction", "url": "javascript:exploit()"}])


def test_scholarly_deadline_interrupts_a_blocked_body():
    class StalledBody(Response):
        def __init__(self):
            super().__init__(b"")
            self.shutdown_called = threading.Event()
            self.raw = self

        def shutdown(self):
            self.shutdown_called.set()

        def iter_content(self, chunk_size):
            assert self.shutdown_called.wait(2)
            yield b'{"resultList":{"result":[]}}'

    with pytest.raises(ScholarlyTransportError, match="^europe_pmc_timeout$"):
        search_scholarly("scope", timeout_seconds=0.05, get=lambda *_a, **_kw: StalledBody())


def _venue(id_number, issn, **overrides):
    return {
        "jufo_id": id_number, "title": "Cell Stress Methods", "type": {"id": "Series"},
        "issn_print": issn, "level": 2, "level_history": {"2018": "1", "2019": 0, "2026": "2"},
        "panels": [6, 7], "okm_disciplines": [
            {"id": "1182", "localized_labels": {"en": "Biochemistry, cell and molecular biology 1182"}},
        ],
        **overrides,
    }


def test_venue_standing_uses_exact_issn_requested_year_and_current_panel_context():
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs["params"]))
        assert kwargs["allow_redirects"] is False
        return Response(json.dumps([_venue(12, "2043-0021"), _venue(42, "2042-0021")]).encode())

    result = lookup_venue("2042-0021", 2018, get=get)
    assert calls == [(JUFO_SEARCH_URL, {"issn": "2042-0021", "type": "series", "_size": 12})]
    assert result == VenueStanding(
        issn="2042-0021", journal="Cell Stress Methods", year=2018, level=1,
        current_panels=(6, 7), current_subjects=("Biochemistry, cell and molecular biology 1182",),
        url="https://jfp.csc.fi/jufoportal?Jufo_ID=42",
        record_url="https://jufo-rest.csc.fi/v2.1/channel/42",
    )


@pytest.mark.parametrize(("rows", "year"), [
    ([_venue(42, "2042-0021")], 2017),
    ([_venue(42, "2042-0021")], 2019),
    ([_venue(12, "2043-0021")], 2018),
    ([_venue(12, "2042-0021"), _venue(42, "2042-0021")], 2018),
])
def test_venue_unknown_stays_unknown_for_missing_tier_or_doubtful_identity(rows, year):
    assert lookup_venue("2042-0021", year, get=lambda *_a, **_kw: Response(json.dumps(rows).encode())) is None


def test_venue_provider_errors_are_fixed_safe_codes():
    with pytest.raises(VenueTransportError, match="^jufo_rate_limited$") as exc:
        lookup_venue("2042-0021", 2018, get=lambda *_a, **_kw: Response(b"raw response detail", 429))
    assert str(exc.value) in VENUE_FAILURE_CODES
