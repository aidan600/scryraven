from dataclasses import dataclass
from typing import Any


@dataclass
class UIContext:
    st: Any
    os: Any
    json: Any
    time: Any
    uuid: Any

    OUTPUT_DIR: Any
    current_date: str
    DEFAULT_SYSTEM: Any
    NEWS_PREFERRED_DOMAINS: Any
    ACADEMIC_DOMAINS: Any
    QUANT_REPORT_TYPES: Any

    logger: Any

    load_history: Any
    save_session: Any
    rename_session: Any
    delete_session: Any

    parse_domain_list: Any
    clean_json_response: Any
    clean_markdown_for_snippet: Any
    safe_stream: Any
    ask_model: Any
    embed_texts: Any
    compute_similarities: Any
    process_search_queries: Any
    get_followup_search_params: Any
    filter_top_evidence: Any
    is_plausible_domain: Any
    anchor_query_to_topic: Any
    fetch_linkup_precision_block: Any
    run_economist_step: Any
