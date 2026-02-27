#!/usr/bin/env python3
"""
Synchronise toutes les équipes (clubs, blasons, diminutifs) vers Supabase.
À lancer une fois après configuration Supabase, puis éventuellement en cron (ex. 1×/semaine).

Crée/met à jour la table teams avec : slug (id API), name, logo_url, search_terms (nom + alias pour recherche rapide).

Prérequis:
  - .env avec API_FOOTBALL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY (ou SUPABASE_KEY)
  - Table teams avec colonne search_terms (texte). Si absente :
    ALTER TABLE teams ADD COLUMN IF NOT EXISTS search_terms text;

Usage:
  cd backend && .\\venv\\Scripts\\python.exe scripts/sync_teams_to_supabase.py
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)

try:
    import pydantic_settings  # noqa: F401
except ImportError:
    print("Active le venv du backend puis relance le script.")
    sys.exit(1)


def _build_search_terms(name: str) -> str:
    """Construit la chaîne search_terms : nom normalisé + alias qui matchent (psg, aja, om...)."""
    from app.services.api_football import _normalize_for_search, TEAM_SEARCH_ALIASES
    n = _normalize_for_search(name or "")
    parts = [n] if n else []
    for alias_key, alias_parts in TEAM_SEARCH_ALIASES.items():
        if any(p in n for p in alias_parts):
            parts.append(alias_key)
    return ",".join(parts)


def main() -> None:
    from app.core.config import get_settings
    from app.core.leagues import LEAGUE_IDS, current_season
    from app.services.api_football import _use_api, get_teams_by_league

    settings = get_settings()
    if not _use_api():
        print("API_FOOTBALL_KEY manquant dans .env")
        sys.exit(1)
    if not (settings.supabase_url and settings.supabase_key):
        print("SUPABASE_URL et SUPABASE_KEY (ou SUPABASE_SERVICE_KEY) requis.")
        sys.exit(1)

    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    season = current_season()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    seen_ids = set()
    rows = []
    for league_id in LEAGUE_IDS:
        try:
            for item in get_teams_by_league(league_id, season):
                t = item.get("team") or item
                tid = t.get("id")
                if tid is None or tid in seen_ids:
                    continue
                seen_ids.add(tid)
                name = (t.get("name") or "").strip()
                if not name:
                    continue
                logo = (t.get("logo") or "").strip() or None
                search_terms = _build_search_terms(name)
                rows.append({
                    "slug": str(tid),
                    "name": name,
                    "logo_url": logo,
                    "search_terms": search_terms,
                    "last_updated": now,
                })
        except Exception as e:
            print(f"Ligue {league_id}: {e}")

    if not rows:
        print("Aucune équipe récupérée. Vérifiez API_FOOTBALL_KEY et les ligues.")
        return

    # Upsert par lots (Supabase limite souvent à 1000 par requête)
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        supabase.table("teams").upsert(batch, on_conflict="slug").execute()
        print(f"Upsert {len(batch)} équipes ({i + len(batch)}/{len(rows)})")

    print(f"Terminé: {len(rows)} équipes en base. La recherche magique utilisera Supabase (rapide).")


if __name__ == "__main__":
    main()
