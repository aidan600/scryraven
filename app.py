import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv

from core.llm import ask_model, compute_similarities, embed_texts
from core.pipeline import (
    QUANT_REPORT_TYPES,
    fetch_linkup_precision_block,
    get_followup_search_params,
    process_search_queries,
    run_economist_step,
    run_scout,
    should_skip_quant_scout,
)
from core.prompts import DEFAULT_SYSTEM
from core.retrieval import (
    ACADEMIC_DOMAINS,
    NEWS_PREFERRED_DOMAINS,
    anchor_query_to_topic,
    clean_markdown_for_snippet,
    filter_top_evidence,
    is_plausible_domain,
)
from core.storage import configure_storage, delete_session, rename_session, save_session
from core.text_utils import clean_json_response
from proplex.env_aliases import pop_env_alias
from ui.context import UIContext
from ui.storage_cache import invalidate_cached_history, load_history
from ui.theme import STREAMLIT_CUSTOM_CSS

load_dotenv()

st.set_page_config(page_title="ScryRaven", page_icon="🧭", layout="wide")

# --- UI STYLING (see ui/theme.py) ---
st.markdown(STREAMLIT_CUSTOM_CSS, unsafe_allow_html=True)

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
HISTORY_FILE = OUTPUT_DIR / "history.json"

current_date = datetime.now().strftime("%B %d, %Y")

# --- INIT STATE ---
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "focus_academic" not in st.session_state:
    st.session_state["focus_academic"] = False
if "force_intent_news" not in st.session_state:
    st.session_state["force_intent_news"] = False
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# --- Optional env seed for scripted / eval-style runs (headless CLI planned; no subprocess wrapper) ---
_cli_q = pop_env_alias("SCRYRAVEN_RUN_QUERY", "PROPLEX_RUN_QUERY").strip()
_cli_mode = pop_env_alias("SCRYRAVEN_RUN_MODE", "PROPLEX_RUN_MODE").strip() or "Balanced"
if _cli_q:
    st.session_state["research_topic_ta"] = _cli_q
    if _cli_mode in ("Fast", "Balanced", "Deep"):
        st.session_state["strategy"] = _cli_mode
    st.session_state["proplex_auto_run"] = True

# --- STANDARD LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(OUTPUT_DIR / "app.log")]
)
logger = logging.getLogger(__name__)
configure_storage(OUTPUT_DIR, HISTORY_FILE, logger, on_history_mutated=invalidate_cached_history)

# --- HELPER FUNCTIONS ---
def parse_domain_list(raw_text: str) -> List[str]:
    return [x.strip().lower() for x in raw_text.split(",") if x.strip()]

def safe_stream(stream):
    """Safely escapes dollars in the stream outside of code blocks to prevent Streamlit MathJax crashes."""
    in_code_block = False
    backtick_buffer = ""
    for chunk in stream:
        if not isinstance(chunk, str):
            yield chunk
            continue

        processed_chunk = ""
        for char in chunk:
            if char == '`':
                backtick_buffer += char
                if len(backtick_buffer) == 3:
                    in_code_block = not in_code_block
                    processed_chunk += backtick_buffer
                    backtick_buffer = ""
            else:
                if backtick_buffer:
                    processed_chunk += backtick_buffer
                    backtick_buffer = ""
                if char == '$' and not in_code_block:
                    processed_chunk += '\\$'
                else:
                    processed_chunk += char
        yield processed_chunk
    if backtick_buffer:
        yield backtick_buffer

# --- MAIN UI ROUTER ---
from ui.pages import render_ui

render_ui(
    UIContext(
        st=st,
        os=os,
        json=json,
        time=time,
        uuid=uuid,
        OUTPUT_DIR=OUTPUT_DIR,
        current_date=current_date,
        DEFAULT_SYSTEM=DEFAULT_SYSTEM,
        NEWS_PREFERRED_DOMAINS=NEWS_PREFERRED_DOMAINS,
        ACADEMIC_DOMAINS=ACADEMIC_DOMAINS,
        QUANT_REPORT_TYPES=QUANT_REPORT_TYPES,
        logger=logger,
        load_history=load_history,
        save_session=save_session,
        rename_session=rename_session,
        delete_session=delete_session,
        parse_domain_list=parse_domain_list,
        clean_json_response=clean_json_response,
        clean_markdown_for_snippet=clean_markdown_for_snippet,
        safe_stream=safe_stream,
        ask_model=ask_model,
        embed_texts=embed_texts,
        compute_similarities=compute_similarities,
        process_search_queries=process_search_queries,
        get_followup_search_params=get_followup_search_params,
        filter_top_evidence=filter_top_evidence,
        is_plausible_domain=is_plausible_domain,
        anchor_query_to_topic=anchor_query_to_topic,
        fetch_linkup_precision_block=fetch_linkup_precision_block,
        run_economist_step=run_economist_step,
        run_scout=run_scout,
        should_skip_quant_scout=should_skip_quant_scout,
    )
)
