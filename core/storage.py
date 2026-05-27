import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.retrieval import ensure_passage_source_ids

OUTPUT_DIR = Path("output")
HISTORY_FILE = OUTPUT_DIR / "history.json"
logger = logging.getLogger(__name__)
_on_history_mutated: Optional[Callable[[], None]] = None


def configure_storage(
    output_dir: Path,
    history_file: Path,
    storage_logger: Optional[logging.Logger] = None,
    *,
    on_history_mutated: Optional[Callable[[], None]] = None,
) -> None:
    global OUTPUT_DIR, HISTORY_FILE, logger, _on_history_mutated
    OUTPUT_DIR = output_dir
    HISTORY_FILE = history_file
    if storage_logger is not None:
        logger = storage_logger
    _on_history_mutated = on_history_mutated
    OUTPUT_DIR.mkdir(exist_ok=True)


def _notify_history_mutated() -> None:
    cb = _on_history_mutated
    if cb is None:
        return
    try:
        cb()
    except Exception as e:
        logger.warning(f"History mutation callback failed: {e}")


def read_history() -> List[Dict[str, Any]]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("History file corrupted or unreadable. Starting fresh.")
    return []


def save_session(session_data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    session_to_save = dict(session_data)

    top_passages = session_to_save.pop("top_passages", [])
    ensure_passage_source_ids(top_passages)
    passages_file = OUTPUT_DIR / f"{session_to_save['id']}_passages.json"
    try:
        with open(passages_file, "w", encoding="utf-8") as pf:
            json.dump(top_passages, pf)
    except Exception as e:
        logger.error(f"Failed to write passages file {passages_file}: {e}")

    history = read_history()
    existing_idx = next((i for i, s in enumerate(history) if s["id"] == session_to_save["id"]), None)
    if existing_idx is not None:
        history[existing_idx] = session_to_save
    else:
        history.insert(0, session_to_save)

    temp_file = HISTORY_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        temp_file.replace(HISTORY_FILE)
    except Exception as e:
        logger.error(f"Failed to save session history to {HISTORY_FILE}: {e}")
    _notify_history_mutated()


def delete_session(session_id: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    history = read_history()
    history = [s for s in history if s["id"] != session_id]

    temp_file = HISTORY_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        temp_file.replace(HISTORY_FILE)
    except Exception as e:
        logger.error(f"Failed to delete session in {HISTORY_FILE}: {e}")

    passages_file = OUTPUT_DIR / f"{session_id}_passages.json"
    try:
        if passages_file.exists():
            passages_file.unlink()
    except Exception as e:
        logger.error(f"Failed to delete passages file {passages_file}: {e}")
    _notify_history_mutated()


def rename_session(session_id: str, new_title: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    history = read_history()
    for s in history:
        if s["id"] == session_id:
            s["title"] = new_title
            break

    temp_file = HISTORY_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        temp_file.replace(HISTORY_FILE)
    except Exception as e:
        logger.error(f"Failed to rename session in {HISTORY_FILE}: {e}")
    _notify_history_mutated()
