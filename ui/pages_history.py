"""Full-screen Library (thread list + search)."""

from datetime import datetime

from core.retrieval import ensure_passage_source_ids
from ui.context import UIContext


def _thread_sort_key(session: dict) -> float:
    ts = session.get("timestamp") or ""
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return float(datetime.strptime(ts.strip(), fmt).timestamp())
        except ValueError:
            continue
    return 0.0


def render_library_page(context: UIContext) -> None:
    st = context.st
    json = context.json

    OUTPUT_DIR = context.OUTPUT_DIR
    load_history = context.load_history
    clean_markdown_for_snippet = context.clean_markdown_for_snippet

    st.markdown("<h1 style='margin-bottom: 1.5rem;'>Library</h1>", unsafe_allow_html=True)
    sort_order = st.radio(
        "Sort threads",
        ("Newest first", "Oldest first"),
        horizontal=True,
        label_visibility="collapsed",
        key="library_sort_order",
    )
    search_term = st.text_input(
        "🔍 Search your threads...",
        placeholder="Search titles, prompts, or reports...",
        label_visibility="collapsed",
    )
    st.divider()

    history_list = load_history()
    history_list = sorted(history_list, key=_thread_sort_key, reverse=(sort_order == "Newest first"))
    filtered_history = history_list
    if search_term:
        term = search_term.lower()
        filtered_history = [
            s
            for s in history_list
            if term in s.get("title", "").lower()
            or term in s.get("query", "").lower()
            or term in s.get("report", "").lower()
        ]

    if not filtered_history:
        st.info("No threads found.")
    else:
        for s in filtered_history:
            raw_title = s.get("title", s.get("query", "Untitled"))
            snippet = clean_markdown_for_snippet(s.get("report", ""))

            if st.button(raw_title, key=f"hp_open_{s['id']}", help="Open thread"):
                passages_file = OUTPUT_DIR / f"{s['id']}_passages.json"
                if passages_file.exists():
                    try:
                        with open(passages_file, "r", encoding="utf-8") as pf:
                            s["top_passages"] = json.load(pf)
                            ensure_passage_source_ids(s["top_passages"])
                    except Exception:
                        s["top_passages"] = []
                else:
                    s["top_passages"] = []

                st.session_state.current_session = s
                st.session_state.current_page = "thread"
                st.rerun()

            st.markdown(
                f"<p style='color: #4b5563; font-size: 14px; margin-top: -8px; margin-bottom: 4px;'>{snippet}</p>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='color: #9ca3af; font-size: 12px; margin-bottom: 24px;'>🕒 {s.get('timestamp', 'Unknown date')}</p>",
                unsafe_allow_html=True,
            )
            st.write("---")
