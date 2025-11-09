"""Small helper to persist and read feedback events.

This writes newline-delimited JSON to data/feedback.json by default. It will
use portalocker if available for a short exclusive lock on Windows to avoid
concurrent append corruption; otherwise it falls back to simple append mode.
"""

import os
import json
from typing import Any, Dict, Iterable, List, Optional

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DEFAULT_PATH = os.path.join(DATA_DIR, "feedback.json")


def _acquire_file_lock(f):
    """Try to lock file if portalocker is installed."""
    try:
        import portalocker

        portalocker.lock(f, portalocker.LOCK_EX)
        return True
    except Exception:
        return False


def _release_file_lock(f):
    try:
        import portalocker

        portalocker.unlock(f)
    except Exception:
        pass


def append_event(event: Dict[str, Any], file_path: Optional[str] = None) -> None:
    """Append a single event as a JSON line to the feedback file.

    This function is intentionally small and dependency-light. For higher
    throughput or strict concurrency guarantees, swap to SQLite or a
    message-queue.
    """
    file_path = file_path or DEFAULT_PATH
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # use binary mode for portalocker compatibility
    with open(file_path, "a", encoding="utf-8") as f:
        locked = _acquire_file_lock(f)
        try:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
        finally:
            if locked:
                _release_file_lock(f)


def append_events(
    events: Iterable[Dict[str, Any]], file_path: Optional[str] = None
) -> int:
    """Append multiple events. Returns number appended."""
    count = 0
    for e in events:
        append_event(e, file_path=file_path)
        count += 1
    return count


def read_events(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    file_path = file_path or DEFAULT_PATH
    if not os.path.exists(file_path):
        return []
    out: List[Dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                # skip malformed lines
                continue
    return out


def get_session_events(
    session_id: str, file_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return events matching session_id (naive scan)."""
    events = read_events(file_path=file_path)
    return [e for e in events if e.get("session_id") == session_id]
