"""One JSON file per trip: data/trips/<trip_id>.json. Swap this module for a DB later."""
import json, os, re, secrets, threading
from pathlib import Path

DATA = Path(os.environ.get("TRIP_DATA_DIR", "data/trips"))
DATA.mkdir(parents=True, exist_ok=True)
_lock = threading.RLock()
_ID = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


def _path(tid):
    return DATA / f"{tid}.json" if _ID.match(tid or "") else None


def load_trip(tid):
    p = _path(tid)
    if not p or not p.exists():
        return None
    with _lock:
        return json.loads(p.read_text("utf-8"))


def save_trip(trip):
    p = _path(trip["id"])
    tmp = p.with_suffix(".tmp")
    with _lock:
        tmp.write_text(json.dumps(trip, indent=2, ensure_ascii=False), "utf-8")
        os.replace(tmp, p)  # atomic: a crash never leaves a half-written file


def update_trip(tid, fn):
    """Read-modify-write under one lock so simultaneous edits don't overwrite each other."""
    with _lock:
        t = load_trip(tid)
        fn(t)
        save_trip(t)
        return t


def new_trip(name, currency="₹"):
    t = {"id": secrets.token_urlsafe(9), "name": name, "currency": currency, "members": [], "expenses": []}
    save_trip(t)
    return t
