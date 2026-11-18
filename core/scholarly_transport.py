"""Public scholarly acquisition and publication context."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from contextlib import closing, nullcontext
from copy import copy
from dataclasses import dataclass
from html.parser import HTMLParser
from time import monotonic
from typing import Annotated, Any, Literal
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree

import requests
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from urllib3.util import Timeout

EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
_JUFO_API = "https://jufo-rest.csc.fi/v2.1"
JUFO_SEARCH_URL = f"{_JUFO_API}/search"
DEFAULT_TIMEOUT_SECONDS = 20.0
SEARCH_PAGE_SIZE = 8
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_ABSTRACT_CHARACTERS = 24_000
_SHARED_FAILURES = {
    "access_rejected", "endpoint_failed", "endpoint_redirected", "json_invalid",
    "material_unavailable", "rate_limited", "response_invalid", "response_too_large",
    "timeout", "transport_failed",
}
SCHOLARLY_FAILURE_CODES = frozenset({
    *(f"europe_pmc_{reason}" for reason in _SHARED_FAILURES),
    "europe_pmc_identity_mismatch", "europe_pmc_license_unavailable", "europe_pmc_xml_invalid",
})
VENUE_FAILURE_CODES = frozenset(f"jufo_{reason}" for reason in _SHARED_FAILURES)

_DOI = re.compile(r"10\.[0-9]{4,9}/[^\s<>\x00-\x1f]{1,230}", re.IGNORECASE)
_PMCID = re.compile(r"PMC[0-9]{1,12}")
_PMID = re.compile(r"[1-9][0-9]{0,10}")
_EXACT_DOI_QUERY = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.[0-9]{4,9}/[-._;()/:a-z0-9]{1,230})",
    re.IGNORECASE | re.ASCII,
)
_EXACT_PMID_QUERY = re.compile(
    rf"(?:PMID:\s*|https?://pubmed\.ncbi\.nlm\.nih\.gov/)({_PMID.pattern})/?",
    re.IGNORECASE | re.ASCII,
)
_EXACT_PMCID_QUERY = re.compile(
    rf"(?:PMCID:\s*|https?://pmc\.ncbi\.nlm\.nih\.gov/articles/)?({_PMCID.pattern})/?",
    re.IGNORECASE | re.ASCII,
)
_ISSN = re.compile(r"[0-9]{4}-[0-9]{3}[0-9X]")
_SOURCE = re.compile(r"[A-Z]{3}")
_RECORD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
_CC_LICENSE = re.compile(
    r"https?://(?:www\.)?creativecommons\.org/"
    r"(?:licenses/(?:by|by-sa)/[1-4]\.0(?:/[a-z]{2})?|publicdomain/(?:zero|mark)/1\.0)/?",
    re.IGNORECASE,
)
_HTTP_CC_LICENSE = re.compile(r"https?://(?:www\.)?creativecommons\.org/[^\s<>\"']+")
_XLINK = "{http://www.w3.org/1999/xlink}href"


def _https_url(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 2048 or any(
        c.isspace() or ord(c) < 33 or c == "\\" for c in value
    ):
        return None
    try:
        url = urlsplit(value)
        if url.scheme == "https" and url.hostname and "." in url.hostname and not (url.username or url.password):
            return value
    except ValueError:
        pass
    return None


def _require_https_url(value: str) -> str:
    if _https_url(value) is None:
        raise ValueError("expected a public HTTPS URL")
    return value

PublicationStatus = Literal["preprint", "published", "retracted"]
RelationKind = Literal[
    "published_version", "preprint", "correction", "corrects", "retraction",
    "retracts", "expression_of_concern", "expression_of_concern_for",
]
PublicationVersion = Literal["author_manuscript", "published", "unknown"]
_Label = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=300)]
_URL = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2048), AfterValidator(_require_https_url)]
_DoiValue = Annotated[str, StringConstraints(strict=True, pattern=r"^10\.[0-9]{4,9}/[^\s<>]{1,230}$")]
_PmcidValue = Annotated[str, StringConstraints(strict=True, pattern=r"^PMC[0-9]{1,12}$")]
_PmidValue = Annotated[str, StringConstraints(strict=True, pattern=r"^[1-9][0-9]{0,10}$")]
_IssnValue = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9]{4}-[0-9]{3}[0-9X]$")]


class PublicationRelation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: RelationKind
    url: _URL
    note: _Label | None = None


class PublicationIndexing(BaseModel):
    """A positive index observation about the record, with its subject scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["NLM Index Medicus"] = "NLM Index Medicus"
    field: Literal["Biomedicine and life sciences"] = "Biomedicine and life sciences"


class PublicationMetadata(BaseModel):
    """Navigation and publication context, kept apart from the acquired text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["Europe PMC"] = "Europe PMC"
    doi: _DoiValue | None = None
    pmid: _PmidValue | None = None
    pmcid: _PmcidValue | None = None
    authors: tuple[_Label, ...] = Field(default=(), max_length=30)
    journal: _Label | None = None
    year: Annotated[int, Field(strict=True, ge=1000, le=9999)] | None = None
    article_types: tuple[_Label, ...] = Field(default=(), max_length=12)
    status: PublicationStatus | None = None
    issns: tuple[_IssnValue, ...] = Field(default=(), max_length=2)
    related: tuple[PublicationRelation, ...] = Field(default=(), max_length=12)
    indexing: PublicationIndexing | None = None
    version: PublicationVersion | None = None
    open_access_url: _URL | None = None
    open_article_available: Annotated[bool, Field(strict=True)] = False

    def landing_urls(self) -> tuple[str, ...]:
        """Public navigation targets supplied or identified by the record."""
        return tuple(dict.fromkeys(url for url in (
            f"https://doi.org/{quote(self.doi, safe='/')}" if self.doi else None,
            _pubmed_url(self.pmid) if self.pmid else None,
            _pmc_url(self.pmcid) if self.pmcid else None,
            self.open_access_url,
        ) if url))


class VenueStanding(BaseModel):
    """The exact requested register year, with the panel context of the current record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issn: _IssnValue
    source: Literal["Finnish Publication Forum (JUFO)"] = "Finnish Publication Forum (JUFO)"
    journal: _Label
    year: Annotated[int, Field(strict=True, ge=1000, le=9999)]
    level: Annotated[int, Field(strict=True, ge=1, le=3)]
    current_panels: tuple[Annotated[int, Field(strict=True, gt=0)], ...] = Field(default=(), max_length=8)
    current_subjects: tuple[_Label, ...] = Field(default=(), max_length=8)
    url: _URL
    record_url: _URL | None = None


@dataclass(frozen=True, slots=True)
class ScholarlyCandidate:
    url: str
    title: str
    abstract: str
    publication: PublicationMetadata
    full_text_pmcid: str | None = None


@dataclass(frozen=True, slots=True)
class ScholarlyFullText:
    url: str
    content: str
    license_url: str
    version: PublicationVersion


class ScholarlyTransportError(RuntimeError):
    """Only fixed safe diagnostics cross the transport boundary."""


class VenueTransportError(RuntimeError):
    """A fixed safe publication-register diagnostic."""


_RELATIONS: dict[str, RelationKind] = {
    "preprint of": "published_version",
    "preprint in": "preprint",
    "has preprint": "preprint",
    "erratum in": "correction",
    "erratum for": "corrects",
    "corrected and republished in": "correction",
    "corrected and republished from": "corrects",
    "retraction in": "retraction",
    "retraction of": "retracts",
    "expression of concern in": "expression_of_concern",
    "expression of concern for": "expression_of_concern_for",
}


def _field_exact_identifier(query: str) -> str:
    """Field a whole identifier so it selects the record rather than citing papers."""
    term = query.strip()
    if doi := _EXACT_DOI_QUERY.fullmatch(term):
        return f'DOI:"{doi[1]}"'
    if pmid := _EXACT_PMID_QUERY.fullmatch(term):
        return f"EXT_ID:{pmid[1]} AND SRC:MED"
    if pmcid := _EXACT_PMCID_QUERY.fullmatch(term):
        return f"PMCID:{pmcid[1].upper()}"
    return query


def search_scholarly(
    query: str, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    get: Callable[..., Any] | None = None,
    on_dispatch: Callable[[str], None] | None = None,
) -> list[ScholarlyCandidate]:
    """Return relevance-ordered records plus only the actual supplied abstracts."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty text")
    body = _request(
        f"{EUROPE_PMC_API}/search", timeout_seconds, get,
        params={
            "query": _field_exact_identifier(query), "format": "json", "resultType": "core",
            "pageSize": SEARCH_PAGE_SIZE,
        },
        on_dispatch=on_dispatch,
    )
    payload = _json(body, "europe_pmc")
    rows = _rows(payload, "resultList", "result")
    if not isinstance(_mapping(_mapping(payload).get("resultList")).get("result"), list):
        raise ScholarlyTransportError("europe_pmc_response_invalid")
    candidates = []
    seen = set()
    for row in rows:
        candidate = _search_candidate(row)
        if candidate is None:
            continue
        metadata = candidate.publication
        keys = {candidate.url, metadata.doi, metadata.pmid, metadata.pmcid} - {None}
        if seen.isdisjoint(keys):
            candidates.append(candidate)
            seen.update(keys)
        if len(candidates) == SEARCH_PAGE_SIZE:
            break
    return candidates


def lookup_venue(
    issn: str, year: int, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    get: Callable[..., Any] | None = None,
) -> VenueStanding | None:
    """Read an exact JUFO series assessment for the specified year, when available."""
    if not isinstance(issn, str) or not _ISSN.fullmatch(issn):
        raise ValueError("issn must be a hyphenated serial identifier")
    if type(year) is not int or not 1000 <= year <= 9999:
        raise ValueError("year must be a four-digit integer")
    body = _request(JUFO_SEARCH_URL, timeout_seconds, get, provider="jufo",
                    params={"issn": issn, "type": "series", "_size": 12})
    payload = _json(body, "jufo")
    if not isinstance(payload, list):
        raise VenueTransportError("jufo_response_invalid")
    matches = [
        row for row in payload
        if isinstance(row, Mapping) and _mapping(row.get("type")).get("id") == "Series"
        and any(row.get(key) == issn for key in ("issn_print", "issn_electronic", "issnl"))
    ]
    if len(matches) != 1:
        return None
    row = matches[0]
    journal = _label(row.get("title"))
    channel_id = row.get("jufo_id")
    raw_level = _mapping(row.get("level_history")).get(str(year))
    if (not journal or type(channel_id) is not int or not 0 < channel_id < 10 ** 11
            or type(raw_level) not in (str, int) or str(raw_level) not in ("1", "2", "3")):
        return None
    raw_panels = row.get("panels")
    panels = tuple(dict.fromkeys(
        panel for panel in raw_panels if type(panel) is int and panel > 0
    ))[:8] if isinstance(raw_panels, list) else ()
    raw_subjects = row.get("okm_disciplines")
    subjects = _labels([
        _mapping(_mapping(item).get("localized_labels")).get("en") for item in raw_subjects
    ], 8) if isinstance(raw_subjects, list) else ()
    return VenueStanding(
        issn=issn, journal=journal, year=year, level=int(raw_level),
        current_panels=panels, current_subjects=subjects,
        url=f"https://jfp.csc.fi/jufoportal?Jufo_ID={channel_id}",
        record_url=f"{_JUFO_API}/channel/{channel_id}",
    )


def fetch_scholarly(
    pmcid: str, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    get: Callable[..., Any] | None = None,
) -> ScholarlyFullText:
    """Read article text from the API's reusable JATS full-text distribution."""
    if not isinstance(pmcid, str) or not _PMCID.fullmatch(pmcid):
        raise ValueError("pmcid must be a PubMed Central identifier")
    xml = _request(f"{EUROPE_PMC_API}/{pmcid}/fullTextXML", timeout_seconds, get)
    try:
        # Standard JATS documents may declare an external DTD. ElementTree does
        # not load it, and internal entity declarations are not needed.
        if re.search(rb"<!\s*ENTITY\b", xml, re.IGNORECASE) or b"\x00" in xml:
            raise ElementTree.ParseError("unsafe JATS declaration")
        article = ElementTree.fromstring(xml)
    except (ElementTree.ParseError, ValueError, RecursionError):
        raise ScholarlyTransportError("europe_pmc_xml_invalid") from None
    meta = article.find("./front/article-meta")
    if article.tag != "article" or meta is None:
        raise ScholarlyTransportError("europe_pmc_material_unavailable")
    ids = {item.get("pub-id-type"): item.text for item in meta.findall("article-id")}
    pmc = ids.get("pmc")
    ids_in_article = {ids.get("pmcid"), pmc, f"PMC{pmc}"}
    if pmcid not in ids_in_article:
        raise ScholarlyTransportError("europe_pmc_identity_mismatch")
    license_url = _article_license(meta)
    if license_url is None:
        raise ScholarlyTransportError("europe_pmc_license_unavailable")
    body_element = article.find("body")
    if body_element is None:
        raise ScholarlyTransportError("europe_pmc_material_unavailable")
    try:
        body = _jats_text(body_element)
        abstracts = [_jats_text(item) for item in meta.findall("abstract") if item.get("abstract-type") is None]
        back = [_jats_text(item) for item in article.findall("back")]
    except RecursionError:
        raise ScholarlyTransportError("europe_pmc_xml_invalid") from None
    if not body:
        raise ScholarlyTransportError("europe_pmc_material_unavailable")
    version: PublicationVersion = "unknown"
    if ids.get("manuscript") or ids.get("nihms") or ids.get("pmcmanuscript"):
        version = "author_manuscript"
    elif article.get("article-version") in {"version-of-record", "vor"}:
        version = "published"
    return ScholarlyFullText(
        _pmc_url(pmcid), "\n\n".join(filter(None, [*abstracts, body, *back])), license_url, version,
    )


def _search_candidate(row: Mapping) -> ScholarlyCandidate | None:
    doi = _identifier(row.get("doi"), _DOI, normalize=str.lower)
    pmid = _identifier(row.get("pmid"), _PMID)
    pmcid = _identifier(row.get("pmcid"), _PMCID, normalize=str.upper)
    source = _identifier(row.get("source"), _SOURCE)
    row_id = _identifier(row.get("id"), _RECORD_ID)
    if not (doi or pmid or pmcid or source and row_id):
        return None

    type_rows = _mapping(row.get("pubTypeList")).get("pubType")
    article_types = _labels(type_rows, 12)
    types = {kind.casefold() for kind in article_types}
    related = _relations(row)
    journal_data = _mapping(_mapping(row.get("journalInfo")).get("journal"))
    journal = _label(journal_data.get("title")) or _label(row.get("journalTitle"))
    is_preprint = source == "PPR" or "preprint" in types
    if not journal and is_preprint:
        journal = _label(_mapping(row.get("bookOrReportDetails")).get("publisher"))
    status: PublicationStatus | None = None
    if "retracted publication" in types or any(r.kind == "retraction" for r in related):
        status = "retracted"
    elif is_preprint:
        status = "preprint"
    elif journal:
        status = "published"

    is_open_full_text = bool(
        pmcid and row.get("isOpenAccess") == "Y" and row.get("inEPMC") == "Y"
    )
    license_label = _label(row.get("license"))
    # Unknown search labels can lead to the documented open subset. The XML
    # license is checked before retaining any article text.
    restrictions = (license_label or "").lower().replace("-", " ").split()
    known_restriction = restrictions[:2] == ["cc", "by"] and bool({"nc", "nd"}.intersection(restrictions))
    full_text_pmcid = pmcid if is_open_full_text and not known_restriction else None
    if full_text_pmcid:
        url = _pmc_url(full_text_pmcid)
    elif doi:
        url = f"https://doi.org/{quote(doi, safe='/')}"
    elif pmid:
        url = _pubmed_url(pmid)
    elif pmcid:
        url = _pmc_url(pmcid)
    else:
        url = f"https://europepmc.org/article/{source}/{row_id}"

    author_rows = _rows(row, "authorList", "author")
    authors = tuple(
        name for author in author_rows
        if (name := _label(author.get("fullName")) or _label(author.get("collectiveName")))
    )[:30]
    if not authors and (author_string := _label(row.get("authorString"))):
        authors = (author_string,)
    year_text = str(row.get("pubYear"))
    indexing = None
    if source == "MED" and any(
        item.get("code") == "IM" for item in _rows(row, "subsetList", "subset")
    ):
        indexing = PublicationIndexing()
    issns = tuple(dict.fromkeys(
        code for field in ("issn", "essn")
        if (code := _identifier(journal_data.get(field), _ISSN, normalize=str.upper))
    ))
    version: PublicationVersion | None = None
    if full_text_pmcid and any(row.get(field) == "Y" for field in ("authMan", "epmcAuthMan", "nihAuthMan")):
        version = "author_manuscript"
    publication = PublicationMetadata(
        doi=doi, pmid=pmid, pmcid=pmcid, authors=authors, journal=journal,
        year=int(year_text) if re.fullmatch(r"[1-9][0-9]{3}", year_text) else None,
        article_types=article_types, status=status, issns=issns, related=related, indexing=indexing,
        version=version, open_access_url=_open_access_url(row), open_article_available=bool(full_text_pmcid),
    )
    title = _label(_abstract_text(row.get("title"))) or doi or pmid or pmcid or row_id
    return ScholarlyCandidate(url, title, _abstract_text(row.get("abstractText")), publication, full_text_pmcid)


def _relations(row: Mapping) -> tuple[PublicationRelation, ...]:
    related = []
    seen = set()
    for link in _rows(row, "commentCorrectionList", "commentCorrection"):
        kind = _RELATIONS.get((_label(link.get("type")) or "").casefold())
        record_id = _identifier(link.get("id"), _RECORD_ID)
        if not kind or not record_id:
            continue
        if link.get("source") == "MED" and _PMID.fullmatch(record_id):
            url = _pubmed_url(record_id)
        elif link.get("source") == "PPR":
            url = f"https://europepmc.org/article/PPR/{record_id}"
        else:
            continue
        if (kind, url) in seen:
            continue
        seen.add((kind, url))
        related.append(PublicationRelation(kind=kind, url=url, note=_label(link.get("note"))))
        if len(related) == 12:
            break
    return tuple(related)


def _open_access_url(row: Mapping) -> str | None:
    links = [
        (item.get("documentStyle") != "html", url)
        for item in _rows(row, "fullTextUrlList", "fullTextUrl")
        if item.get("availabilityCode") in ("OA", "F")
        and item.get("site") not in {"DOI", "Europe_PMC"}
        and (url := _https_url(item.get("url")))
    ]
    return min(links)[1] if links else None


def _request(url, timeout_seconds, get, *, params=None, on_dispatch=None, provider="europe_pmc") -> bytes:
    from scryraven.chatgpt_plan.http import PlanError, response_deadline

    error = VenueTransportError if provider == "jufo" else ScholarlyTransportError
    timeout = float(timeout_seconds)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    end = monotonic() + timeout
    if on_dispatch is not None:
        try:
            on_dispatch(params["query"])
        except Exception:
            pass  # Optional activity cannot prevent dispatch.
    try:
        with (nullcontext() if get is not None else closing(requests.Session())) as session:
            if session is not None:
                session.trust_env = False
                get = session.get
            with get(
                url, params=params, timeout=Timeout(total=timeout, connect=timeout, read=timeout),
                allow_redirects=False, stream=True, headers={"User-Agent": "ScryRaven scholarly retrieval"},
            ) as response:
                if 300 <= response.status_code < 400:
                    raise error(f"{provider}_endpoint_redirected")
                response.raise_for_status()
                body = bytearray()
                with response_deadline(response, end - monotonic()):
                    for chunk in response.iter_content(64 * 1024):
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise error(f"{provider}_response_too_large")
    except (PlanError, requests.exceptions.Timeout):
        raise error(f"{provider}_timeout") from None
    except requests.exceptions.HTTPError as exc:
        code = {
            401: "access_rejected", 403: "access_rejected",
            404: "material_unavailable", 429: "rate_limited",
        }.get(getattr(exc.response, "status_code", None), "endpoint_failed")
        raise error(f"{provider}_{code}") from None
    except requests.exceptions.RequestException:
        raise error(f"{provider}_transport_failed") from None
    return bytes(body)


def _json(body: bytes, provider: str) -> Any:
    try:
        return json.loads(body)
    except (ValueError, RecursionError):
        error = VenueTransportError if provider == "jufo" else ScholarlyTransportError
        raise error(f"{provider}_json_invalid") from None


def _mapping(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _rows(parent: Any, collection: str, member: str) -> list[Mapping]:
    rows = _mapping(_mapping(parent).get(collection)).get(member)
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _identifier(value: Any, pattern: re.Pattern, *, normalize=lambda text: text) -> str | None:
    if not isinstance(value, str):
        return None
    value = normalize(value.strip())
    return value if pattern.fullmatch(value) else None


def _label(value: Any) -> str | None:
    return (" ".join(value.split())[:300] or None) if isinstance(value, str) else None


def _labels(values: Any, limit: int) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(dict.fromkeys(label for value in values if (label := _label(value))))[:limit]


def _pmc_url(pmcid: str) -> str:
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"


def _pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


_BLOCK_TAGS = {
    "br", "div", "label", "list", "list-item", "li", "p", "sec", "title",
    "h1", "h2", "h3", "h4", "h5", "h6", "fig", "table", "table-wrap", "tr",
}
_SEPARATOR = {**dict.fromkeys(_BLOCK_TAGS, "\n"), "td": "\t", "th": "\t"}
_SCRIPT_OPEN = {"sub": "_{", "sup": "^{"}


class _AbstractParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        self.parts.append(_SCRIPT_OPEN.get(tag, _SEPARATOR.get(tag, "")))

    def handle_endtag(self, tag):
        self.parts.append("}" if tag in _SCRIPT_OPEN else _SEPARATOR.get(tag, ""))


def _abstract_text(value: Any) -> str:
    if not isinstance(value, str) or len(value) > MAX_ABSTRACT_CHARACTERS:
        return ""
    parser = _AbstractParser()
    parser.feed(value)
    parser.close()
    return _clean_lines("".join(parser.parts))


def _clean_lines(text: str) -> str:
    return "\n".join(line for part in text.splitlines() if (line := part.strip()))


def _jats_text(node: ElementTree.Element) -> str:
    """Deterministic readable extraction from the supplied XML, without summaries."""
    def render(element: ElementTree.Element):
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "alternatives" and (tex := element.find("tex-math")) is not None:
            yield from render(tex)
            return
        if tag == "math":
            # Flattening MathML, such as fractions or powers, changes the
            # reported value. Retain its supplied alternative or original markup.
            alternative = element.get("alttext")
            if alternative:
                yield alternative
            else:
                original = copy(element)
                original.tail = None
                yield ElementTree.tostring(original, encoding="unicode")
            return
        separator = _SEPARATOR.get(tag, "")
        yield _SCRIPT_OPEN.get(tag, separator)
        yield element.text or ""
        for child in element:
            yield from render(child)
            yield child.tail or ""
        yield "}" if tag in _SCRIPT_OPEN else separator

    return _clean_lines("".join(render(node)))


def _article_license(meta: ElementTree.Element) -> str | None:
    licenses = meta.findall("./permissions/license")
    for license_node in licenses:
        urls = [
            link
            for element in license_node.iter()
            if (link := element.get(_XLINK) or element.get("href")) and _CC_LICENSE.fullmatch(link)
        ]
        urls.extend(
            url.rstrip(".,)") for url in _HTTP_CC_LICENSE.findall("".join(license_node.itertext()))
            if _CC_LICENSE.fullmatch(url.rstrip(".,)"))
        )
        if urls:
            return re.sub(r"^http://", "https://", urls[0], flags=re.IGNORECASE)
    return None
