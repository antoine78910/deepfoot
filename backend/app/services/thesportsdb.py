"""TheSportsDB (free) — next fixtures for a named club. Cached on disk, no API-Football quota."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "thesportsdb"
_CACHE_DIR = _DATA_DIR / "cache"
_BASE = "https://www.thesportsdb.com/api/v1/json/123"
_SEARCH_TTL = 7 * 24 * 3600
_EVENTS_TTL = 6 * 3600

_SEARCH_ALIASES: dict[str, str] = {
    "paris saint germain": "Paris Saint Germain",
    "bayern munchen": "Bayern Munich",
    "bayern munich": "Bayern Munich",
    "internazionale": "Inter",
    "atletico madrid": "Atletico Madrid",
    "olympique marseille": "Marseille",
    "olympique lyon": "Lyon",
}


def _normalize(s: str) -> str:
    import unicodedata

    n = unicodedata.normalize("NFD", (s or "").strip().lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.replace("-", " ").replace(".", " ")
    return " ".join(n.split())


def _ensure_cache_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(kind: str, key: str) -> Path:
    digest = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.json"


def _read_cache(kind: str, key: str, ttl: int) -> Optional[Any]:
    fp = _cache_path(kind, key)
    if not fp.exists():
        return None
    try:
        payload = json.loads(fp.read_text(encoding="utf-8"))
        stored_at = float(payload.get("stored_at") or 0)
        if time.time() - stored_at > ttl:
            return None
        return payload.get("data")
    except (OSError, ValueError, TypeError):
        return None


def _write_cache(kind: str, key: str, data: Any) -> None:
    try:
        _ensure_cache_dir()
        fp = _cache_path(kind, key)
        fp.write_text(
            json.dumps({"stored_at": time.time(), "data": data}, default=str),
            encoding="utf-8",
        )
    except OSError:
        pass


def _http_get(path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{_BASE}{path}" if path.startswith("/") else f"{_BASE}/{path}"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params=params)
        r.raise_for_status()
        return r.json() or {}
    except Exception as exc:
        print(f"[thesportsdb] GET {path} error: {exc}")
        return {}


def format_event_for_upcoming(ev: dict) -> Optional[dict]:
    """Convert one TheSportsDB event to the LP upcoming card shape. None if not playable."""
    if not isinstance(ev, dict):
        return None
    status = (ev.get("strStatus") or "").strip().upper()
    if status in ("FT", "MATCH FINISHED", "AET", "PEN", "AWARDED", "POSTP"):
        return None
    ts = (ev.get("strTimestamp") or "").strip()
    date_event = (ev.get("dateEvent") or "")[:10]
    time_raw = (ev.get("strTime") or "").strip()
    dt = None
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
    if dt is None and date_event:
        try:
            hhmm = time_raw[:8] if time_raw and time_raw[0].isdigit() else "00:00:00"
            dt = datetime.fromisoformat(f"{date_event}T{hhmm}").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
    if dt is not None and dt < datetime.now(timezone.utc):
        return None
    home = (ev.get("strHomeTeam") or "").strip()
    away = (ev.get("strAwayTeam") or "").strip()
    if not home or not away:
        return None
    return {
        "date": dt.strftime("%d/%m") if dt else "",
        "time": dt.strftime("%H:%M") if dt else "",
        "league": {"name": (ev.get("strLeague") or "").strip() or None},
        "home": {"name": home, "logo": (ev.get("strHomeTeamBadge") or "").strip() or None},
        "away": {"name": away, "logo": (ev.get("strAwayTeamBadge") or "").strip() or None},
    }


def _pick_team(rows: list[dict], query: str) -> Optional[dict]:
    qn = _normalize(query)
    scored: list[tuple[int, dict]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("strTeam") or "").strip()
        if not name:
            continue
        sport = (row.get("strSport") or "").strip().lower()
        if sport and sport not in ("soccer", "association football", ""):
            continue
        nn = _normalize(name)
        league = _normalize(row.get("strLeague") or "")
        if any(tok in nn for tok in ("talon", "esport", " u19", " u21", " women", " wfc")):
            continue
        if nn == qn:
            score = 0
        elif qn in nn or nn in qn:
            score = 1
        else:
            continue
        if "esports" in league or "mobile" in league:
            continue
        scored.append((score, row))
    scored.sort(key=lambda x: (x[0], x[1].get("strTeam") or ""))
    return scored[0][1] if scored else None


def resolve_team_id(team_name: str) -> Optional[str]:
    name = (team_name or "").strip()
    if not name:
        return None
    key = _normalize(name)
    cached = _read_cache("team", key, _SEARCH_TTL)
    if isinstance(cached, str) and cached:
        return cached
    search = _SEARCH_ALIASES.get(key) or name
    data = _http_get("/searchteams.php", {"t": search})
    rows = data.get("teams") or []
    if not isinstance(rows, list):
        rows = []
    picked = _pick_team(rows, search)
    if not picked:
        return None
    tid = str(picked.get("idTeam") or "").strip()
    if not tid:
        return None
    _write_cache("team", key, tid)
    return tid


def get_upcoming_for_team(team_name: str, limit: int = 10) -> list[dict]:
    """Next fixtures for a club name (cached). Empty if unknown or none scheduled."""
    tid = resolve_team_id(team_name)
    if not tid:
        return []
    cached = _read_cache("events", tid, _EVENTS_TTL)
    events: list[dict]
    if isinstance(cached, list):
        events = [e for e in cached if isinstance(e, dict)]
    else:
        data = _http_get("/eventsnext.php", {"id": tid})
        raw = data.get("events") or []
        events = [e for e in raw if isinstance(e, dict)]
        _write_cache("events", tid, events)
    out: list[dict] = []
    for ev in events:
        row = format_event_for_upcoming(ev)
        if not row:
            continue
        out.append(row)
        if len(out) >= limit:
            break
    return out
