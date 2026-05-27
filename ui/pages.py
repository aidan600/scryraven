"""Streamlit UI router: dispatches to focused page modules."""

from ui.context import UIContext
from ui.pages_history import render_library_page
from ui.pages_home import render_home_page
from ui.pages_sidebar import render_main_sidebar, render_review_mode_toggle
from ui.pages_thread import render_thread_page


def render_ui(context: UIContext) -> None:
    render_review_mode_toggle(context)

    st = context.st

    if st.session_state.current_page == "history":
        render_library_page(context)
    elif st.session_state.current_session is None:
        render_home_page(context)
    else:
        render_thread_page(context)

    render_main_sidebar(context)
