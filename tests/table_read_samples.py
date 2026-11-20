"""Full-length synthetic table content; no provider calls or research claims."""

from dataclasses import replace
from hashlib import sha256

from reading_room_samples import no_io

from scryraven.reading_room import create_app
from scryraven.results import CompletedAnswer, resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence, SupportRegion

QUESTION = "Compare three fictional cheese samples without shortening the tasting notes."
HEADERS = ("Cheese", "Flavour and texture", "Serving and keeping")
SOURCE_URL = "https://example.org/synthetic-cheese-notes"
SOURCE_TITLE = "Synthetic cheese tasting notes"
LAST_CELL_MARKER = "CheeseComparisonLastCellMarker"
LAST_CELL_URL = "https://example.org/synthetic-cheese-last-cell"
SAVED_PASSAGE = "The fictional Brie sample has a soft centre and a mild rind."
SOURCE_BODY = (
    "Synthetic fixture only; these are invented tasting notes, not food-storage advice.\n\n"
    + SAVED_PASSAGE
    + "\n\nThe fictional Cheddar sample is firm, and the fictional blue sample is crumbly. "
    "The tasting team compares complete notes rather than selecting a winner."
)

ROWS = (
    (
        "Brie",
        "The fictional Brie sample starts with a **soft, creamy centre** and a mild rind, followed by a gentle "
        "mushroom note that becomes easier to notice as the piece warms on the plate. The panel describes the "
        "texture separately from the flavour so that a reader can compare the full observation with the firmer "
        "samples below instead of relying on a short label. [E1]",
        "For this invented serving exercise, the team puts a small wedge beside plain bread and sliced pear, "
        "then records which pairing leaves the delicate flavour easiest to notice. Its worksheet keeps the "
        "original wrapping beside the sample and marks the `cut-side` clearly so that the next observation "
        "refers to the same piece. These details belong to the fictional comparison rather than practical "
        "food-storage guidance.",
    ),
    (
        "Cheddar",
        "The fictional Cheddar sample feels firm at first and breaks into small flakes when the panel cuts "
        "a thicker piece. Its *rounded, savoury flavour* develops gradually rather than arriving all at once, "
        "and the notes distinguish a lingering nutty impression from the sharper finish. The full paragraph "
        "matters here because those observations describe different parts of the tasting sequence and should "
        "not collapse into a two-word summary.",
        "In the made-up comparison, the Cheddar sits beside an apple slice and a neutral cracker so the "
        "panel can alternate between a crisp accompaniment and a plain one. A labelled paper sleeve records "
        "the sample number, the cut used for the tasting and the order of the observations. Keeping those "
        "notes together lets a later reader understand the comparison without guessing which short label "
        "belonged to which piece.",
    ),
    (
        "Blue cheese",
        "The fictional blue sample is crumbly near the edge and smoother toward its centre, with a more "
        "pronounced aroma than either of the other pieces. The panel records a salty opening, a tangy middle "
        "and an earthy finish as separate impressions rather than calling the whole sample simply strong. "
        "Readers need the complete sequence to compare the notes fairly, especially when a table contains "
        "several similarly long descriptions side by side.",
        "For the final invented serving exercise, the team uses a plain oat biscuit and a small piece of "
        "pear, tasting each separately before returning to the cheese. Its comparison sheet records the "
        "portion, the pairing order and the comments that changed after a second taste, preserving every "
        "qualification for the next reader. The last note has a unique linked marker so export checks can "
        f"confirm that the final cell appears exactly once: {LAST_CELL_MARKER}.",
    ),
)

COMPACT_NUMERIC_TABLE = """| Sample | Score | Pieces |
| --- | ---: | ---: |
| Brie | 7 | 2 |
| Cheddar | 8 | 3 |
| Blue | 6 | 1 |"""

# Direct-DOM browser control only: raw answer HTML remains disabled in production.
COMPLEX_TABLE_HTML = """<table><thead><tr><th rowspan="2">Cheese</th><th colspan="2">Tasting</th></tr>
<tr><th>Texture</th><th>Finish</th></tr></thead><tbody>
<tr><td>Brie</td><td>Soft</td><td>Mild</td></tr></tbody></table>"""


def cheese_result(*, source_url=SOURCE_URL, last_cell_url=LAST_CELL_URL):
    evidence = Evidence("E1", source_url, SOURCE_TITLE, SOURCE_BODY)
    table = "\n".join(("| " + " | ".join(HEADERS) + " |", "| --- | --- | --- |",
                       *("| " + " | ".join(row) + " |" for row in ROWS)))
    draft = "Synthetic comparison only. Every paragraph below is invented for layout checks.\n\n" + table
    prose, citations, uses = resolve_citations(draft, [evidence], [evidence], [])
    start = SOURCE_BODY.index(SAVED_PASSAGE)
    support = SupportRegion(evidence.id, start, start + len(SAVED_PASSAGE),
                            sha256(SOURCE_BODY.encode()).hexdigest(), sha256(SAVED_PASSAGE.encode()).hexdigest())
    uses = (replace(uses[0], support=(support,)),)
    # Historical answers may contain ordinary links. Put this one after the only
    # citation so its exact saved coordinates stay unchanged by Markdown syntax.
    prose = prose.replace(LAST_CELL_MARKER, f"[{LAST_CELL_MARKER}]({last_cell_url})")
    return CompletedAnswer(prose, "supported", "supported", (evidence,), (), (evidence,), citations, uses)


def make_table_fixture(database, *, source_url=SOURCE_URL, last_cell_url=LAST_CELL_URL):
    """Return the ordinary app and path for one committed historical answer."""
    result = cheese_result(source_url=source_url, last_cell_url=last_cell_url)
    store = SQLiteSessionStore(database)
    session = ResearchSession.create(store=store, engine=lambda question, **kwargs: result,
                                     model=no_io, search=no_io, fetch=no_io)
    session.ask(QUESTION)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    return app, f"/sessions/{session.session_id}"
