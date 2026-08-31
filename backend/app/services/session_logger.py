import json
import os
from datetime import datetime, timezone

# When DATA_DIR is set (e.g. a Railway volume mounted at /data), all logs go
# there so they survive redeploys. Default keeps the local repo layout.
_DATA_DIR = os.environ.get("DATA_DIR")
_LOG_DIR = (
    os.path.join(_DATA_DIR, "logs") if _DATA_DIR
    else os.path.join(os.path.dirname(__file__), "../../../logs")
)


def log_event(session_id: str, event: str, data: dict) -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event": event,
        **data,
    }
    path = os.path.join(_LOG_DIR, f"{session_id}.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    # Mirror session_start events to a shared index for easy cross-user review
    if event == "session_start":
        index_path = os.path.join(_LOG_DIR, "starts.jsonl")
        with open(index_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def get_all_sessions() -> list:
    if not os.path.isdir(_LOG_DIR):
        return []
    sessions = []
    for fname in sorted(os.listdir(_LOG_DIR)):
        if not fname.endswith(".jsonl"):
            continue
        session_id = fname[:-6]
        events = []
        with open(os.path.join(_LOG_DIR, fname)) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        sessions.append({"session_id": session_id, "events": events})
    return sessions


def get_session(session_id: str) -> list:
    path = os.path.join(_LOG_DIR, f"{session_id}.jsonl")
    if not os.path.isfile(path):
        return []
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events
