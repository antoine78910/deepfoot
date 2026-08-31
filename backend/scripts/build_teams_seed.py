"""Build backend/app/data/teams_seed.json from API-Football disk cache (no extra HTTP)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "api-football" / "cache"
OUT = ROOT / "app" / "data" / "teams_seed.json"

SKIP_NAME_PARTS = (
    " u17",
    " u18",
    " u19",
    " u20",
    " u21",
    " u23",
    " women",
    " w ",
    " femin",
)


def _skip_name(name: str) -> bool:
    n = f" {name.lower()} "
    if name.lower().endswith(" w") or name.lower().endswith(" ii") or name.lower().endswith(" iii"):
        return True
    if name.lower().endswith(" b"):
        return True
    return any(p in n or p.strip() in name.lower() for p in SKIP_NAME_PARTS)


def main() -> None:
    teams: dict[int, dict] = {}
    for fp in CACHE_DIR.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (payload.get("path") or "") != "/teams":
            continue
        data = payload.get("data") or {}
        for item in data.get("response") or []:
            team = (item or {}).get("team") or {}
            tid = team.get("id")
            name = (team.get("name") or "").strip()
            logo = (team.get("logo") or "").strip()
            country = (team.get("country") or "").strip()
            if tid is None or not name or not logo or team.get("national"):
                continue
            if _skip_name(name):
                continue
            teams[int(tid)] = {
                "id": int(tid),
                "name": name,
                "crest": logo,
                "country": country or None,
            }
    rows = sorted(teams.values(), key=lambda t: (t.get("country") or "", t["name"].lower()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} teams -> {OUT}")


if __name__ == "__main__":
    main()
