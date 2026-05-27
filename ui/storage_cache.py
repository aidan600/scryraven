"""Streamlit cache for history reads; core/storage performs uncached I/O."""

from __future__ import annotations

import streamlit as st

from core.storage import read_history


@st.cache_data(ttl=5)
def load_history():
    return read_history()


def invalidate_cached_history() -> None:
    load_history.clear()
