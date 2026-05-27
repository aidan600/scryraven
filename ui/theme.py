"""Central Streamlit CSS (light + Streamlit dark theme). Edit here instead of ``app.py``."""

STREAMLIT_CUSTOM_CSS = """
<style>
    .block-container { max-width: 850px !important; padding-top: 3rem !important; padding-bottom: 2rem !important; margin: 0 auto !important; }
    h1 { font-size: 2.2rem !important; font-weight: 700 !important; color: #111827 !important; padding-bottom: 0.5rem !important; }
    h2, h3, h4 { color: #111827 !important; }
    p, li { font-size: 16px !important; line-height: 1.65 !important; color: #374151 !important; }
    img { max-width: 100% !important; height: auto !important; max-height: 450px !important; border-radius: 8px !important; object-fit: contain !important; margin: 1.5rem 0 !important; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); }
    [data-testid="stSidebarHeader"] { display: none !important; }
    [data-testid="stSidebar"] { background-color: #f9f9fb !important; border-right: 1px solid #e5e7eb !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #ffffff !important; border: 1px solid #d1d5db !important; color: #111827 !important; text-align: left !important; justify-content: flex-start !important; border-radius: 8px !important; padding: 0.5rem 0.75rem !important; font-size: 14px !important; font-weight: 500 !important; transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important; }
    [data-testid="stSidebar"] .stButton > button:hover:not(:disabled) { background-color: #f3f4f6 !important; border-color: #9ca3af !important; color: #111827 !important; }
    [data-testid="stExpander"] .stButton > button[kind="secondary"] { background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 0.35rem 0.5rem !important; font-weight: 400 !important; color: #374151 !important; }
    [data-testid="stExpander"] .stButton > button[kind="secondary"]:hover:not(:disabled) { background-color: #eef0f2 !important; }
    [data-testid="stExpander"] .stButton > button[kind="primary"] { background-color: #e5e7eb !important; border: none !important; box-shadow: none !important; padding: 0.35rem 0.5rem !important; font-weight: 600 !important; }
    [data-testid="stExpander"] .stButton > button[kind="primary"] p { color: #111827 !important; font-weight: 600 !important; }
    [data-testid="stPopover"] button svg { display: none !important; }
    [data-testid="stPopover"] button { padding: 0 !important; justify-content: center !important; color: #9ca3af !important; width: 100% !important; min-width: 2rem !important; border: none !important; background: transparent !important; box-shadow: none !important; }
    [data-testid="stPopover"] button:hover { color: #111827 !important; }
    [data-testid="stExpander"] details { border: none !important; background: transparent !important; box-shadow: none !important; }
    [data-testid="stExpander"] summary { background: transparent !important; padding: 0.5rem 0 !important; }
    [data-testid="stExpander"] summary p { font-weight: 600 !important; font-size: 0.85rem !important; color: #6b7280 !important; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stSidebar"] button p { white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; margin: 0 !important; width: 100% !important; text-align: left !important; direction: ltr !important; }
    [data-testid="stTextArea"] div[data-baseweb="base-input"],
    [data-testid="stTextInput"] div[data-baseweb="base-input"] { border-radius: 16px !important; border: 1px solid #e5e7eb !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important; background-color: white !important; transition: all 0.2s ease; }
    [data-testid="stTextArea"] div[data-baseweb="base-input"]:focus-within,
    [data-testid="stTextInput"] div[data-baseweb="base-input"]:focus-within { border-color: #9ca3af !important; box-shadow: 0 0 0 1px #9ca3af !important; }
    [data-testid="stTextArea"] textarea { background-color: transparent !important; padding: 1.2rem !important; font-size: 1.05rem !important; color: #111827 !important; }
    .stButton>button[kind="primary"] { background-color: #ffffff !important; color: #374151 !important; border-radius: 24px !important; font-weight: 500 !important; padding: 0.6rem 2rem !important; border: 1px solid #d1d5db !important; transition: all 0.2s; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important; }
    .stButton>button[kind="primary"]:hover:not(:disabled) { background-color: #f9f9fb !important; border-color: #9ca3af !important; color: #111827 !important; }
    button[title="Open thread"] { background-color: transparent !important; border: none !important; color: #111827 !important; font-size: 1.15rem !important; font-weight: 600 !important; padding: 0 !important; justify-content: flex-start !important; box-shadow: none !important; }
    button[title="Open thread"]:hover:not(:disabled) { color: #4b5563 !important; }
    [data-testid="stChatMessageAvatar"] { display: none !important; }

    /* Streamlit Settings → Theme: Dark */
    [data-testid="stApp"][data-theme="dark"] h1,
    [data-testid="stApp"][data-theme="dark"] h2,
    [data-testid="stApp"][data-theme="dark"] h3,
    [data-testid="stApp"][data-theme="dark"] h4 { color: #f3f4f6 !important; }
    [data-testid="stApp"][data-theme="dark"] p,
    [data-testid="stApp"][data-theme="dark"] li { color: #d1d5db !important; }
    [data-testid="stApp"][data-theme="dark"] [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }
    [data-testid="stApp"][data-theme="dark"] [data-testid="stSidebar"] .stButton > button {
        background-color: #0f172a !important;
        border-color: #475569 !important;
        color: #f3f4f6 !important;
    }
    [data-testid="stApp"][data-theme="dark"] [data-testid="stSidebar"] .stButton > button:hover:not(:disabled) {
        background-color: #334155 !important;
        border-color: #64748b !important;
    }
    [data-testid="stApp"][data-theme="dark"] [data-testid="stTextArea"] div[data-baseweb="base-input"],
    [data-testid="stApp"][data-theme="dark"] [data-testid="stTextInput"] div[data-baseweb="base-input"] {
        background-color: #0f172a !important;
        border-color: #475569 !important;
    }
    [data-testid="stApp"][data-theme="dark"] [data-testid="stTextArea"] textarea {
        color: #f3f4f6 !important;
    }
    [data-testid="stApp"][data-theme="dark"] .stButton>button[kind="primary"] {
        background-color: #1e293b !important;
        color: #e5e7eb !important;
        border-color: #475569 !important;
    }
    [data-testid="stApp"][data-theme="dark"] button[title="Open thread"] {
        color: #f3f4f6 !important;
    }
</style>
"""
