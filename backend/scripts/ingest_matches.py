#!/usr/bin/env python3
"""
Script d'ingestion des matchs / résultats pour Visifoot 2.0.
Source: API-Football (https://www.api-football.com/documentation-v3)
À lancer via cron (ex. 1×/jour) ou manuellement.

Usage (depuis backend, avec l'environnement virtuel activé):
  cd backend
  venv\\Scripts\\activate   (Windows)
  python scripts/ingest_matches.py

Prérequis: venv activé, pip install -r requirements.txt, .env avec API_FOOTBALL_KEY.
"""
import os
import sys
from pathlib import Path

try:
    import pydantic_settings  # noqa: F401
except ImportError:
    print("Erreur: module 'pydantic_settings' introuvable.")
    print("Lance le script avec le venv du backend :")
    print("  PowerShell:  cd backend  puis  .\\run_ingest.ps1")
    print("  Ou:  cd backend  puis  .\\venv\\Scripts\\python.exe scripts/ingest_matches.py")
    print("  CMD:  cd backend  puis  run_ingest.bat")
    sys.exit(1)

from datetime import datetime, timezone

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)


def main() -> None:
    from app.core.config import get_settings
    from app.core.leagues import LEAGUE_IDS, current_season
    from app.services.api_football import (
        _use_api,
        get_fixtures_by_league,
        fixture_for_ingest,
    )

    if not _use_api():
        print("API-Football non configurée. Définir API_FOOTBALL_KEY dans .env ou .env.local")
        print("Clé gratuite: https://www.api-football.com/")
        return

    settings = get_settings()
    has_supabase = bool(settings.supabase_url and settings.supabase_key)
    season = current_season()

    # Récupérer les matchs finis par ligue
    all_fixtures: list[dict] = []
    seen_keys: set[tuple] = set()
    for league_id in LEAGUE_IDS:
        try:
            fixtures = get_fixtures_by_league(league_id, season=season, status="FT")
            for f in fixtures:
                key = (f.get("fixture", {}).get("id"), (f.get("teams") or {}).get("home", {}).get("id"), (f.get("teams") or {}).get("away", {}).get("id"))
                if key not in seen_keys and key[0] and key[1] and key[2]:
                    seen_keys.add(key)
                    all_fixtures.append(f)
        except Exception:
            continue

    print(f"API-Football: {len(all_fixtures)} matchs récupérés (saison {season}, {len(LEAGUE_IDS)} ligues)")

    if not all_fixtures:
        print("Aucun match trouvé. Vérifiez votre clé API et les ligues accessibles.")
        return

    if has_supabase:
        from app.core.supabase_client import get_supabase
        supabase = get_supabase()
        teams_seen: set[str] = set()
        inserted = 0
        for f in all_fixtures:
            row = fixture_for_ingest(f)
            if not row:
                continue
            hid, aid, hname, aname, hg, ag, utc_date, league = row
            for (tid, tname) in [(hid, hname), (aid, aname)]:
                if tid not in teams_seen:
                    teams_seen.add(tid)
                    supabase.table("teams").upsert(
                        {"name": tname, "slug": tid},
                        on_conflict="slug",
                    ).execute()
            existing = supabase.table("results").select("id").eq("home_team_id", hid).eq("away_team_id", aid).eq("date", utc_date).execute()
            if existing.data:
                continue
            supabase.table("results").insert(
                {
                    "home_team_id": hid,
                    "away_team_id": aid,
                    "home_goals": hg,
                    "away_goals": ag,
                    "date": utc_date,
                    "league": league or None,
                },
            ).execute()
            inserted += 1
        print(f"Supabase: results et teams mis à jour ({inserted} nouveaux matchs).")
    else:
        print("Supabase non configuré: pas de persistance.")


if __name__ == "__main__":
    main()
