#!/usr/bin/env python3
"""
Import statique joueurs (1× par saison, stratégie Visifoot).
Pour chaque ligue configurée : GET /teams?league=X&season=Y puis GET /players?team=ID&season=Y.
Stocke en Supabase table players (id, team_id, name, age, nationality, photo_url, position, updated_at).
Ne rappeler qu'en nouvelle saison.

Ligues utilisées : UEFA Champions League, UEFA Europa League, Botola Pro, Bundesliga, Eredivisie,
Jupiler Pro League, La Liga, Ligue 1, Premier League, Primeira Liga, Pro League (Saudi),
Serie A, Super League (Switzerland), Süper Lig.

Prérequis:
  - Table players créée (voir scripts/supabase_players_table.sql)
  - .env avec API_FOOTBALL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY (ou SUPABASE_KEY)

Usage:
  cd backend && .\\venv\\Scripts\\python.exe scripts/sync_players_to_supabase.py
  cd backend && .\\venv\\Scripts\\python.exe scripts/sync_players_to_supabase.py --dry-run
"""
import argparse
import os
import sys
import time
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

# Ligues pour l'import joueurs (ids API-Football)
PLAYER_LEAGUE_IDS = [
    2,   # UEFA Champions League
    3,   # UEFA Europa League
    266, # Botola Pro
    78,  # Bundesliga
    88,  # Eredivisie
    144, # Jupiler Pro League (Belgium)
    140, # La Liga
    61,  # Ligue 1
    39,  # Premier League
    94,  # Primeira Liga
    307, # Pro League (Saudi-Arabia)
    135, # Serie A
    207, # Super League (Switzerland)
    203, # Süper Lig
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync players (by league/team) to Supabase, 1× per season.")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire en base, seulement compter.")
    parser.add_argument("--delay", type=float, default=0.5, help="Délai entre chaque appel /players (s).")
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.core.leagues import current_season
    from app.services.api_football import _use_api, get_teams_by_league, get_players_by_team

    settings = get_settings()
    if not _use_api():
        print("API_FOOTBALL_KEY manquant dans .env")
        sys.exit(1)
    if not args.dry_run and not (settings.supabase_url and settings.supabase_key):
        print("SUPABASE_URL et SUPABASE_KEY requis.")
        sys.exit(1)

    season = current_season()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    all_rows = []

    for league_id in PLAYER_LEAGUE_IDS:
        try:
            teams_raw = get_teams_by_league(league_id, season)
        except Exception as e:
            print(f"Ligue {league_id}: erreur teams {e}")
            continue
        team_ids = []
        for item in teams_raw:
            t = item.get("team") or item
            tid = t.get("id")
            if tid is not None:
                team_ids.append(int(tid))
        if not team_ids:
            continue
        print(f"Ligue {league_id}: {len(team_ids)} équipes")
        for team_id in team_ids:
            try:
                raw = get_players_by_team(team_id, season)
            except Exception as e:
                print(f"  Team {team_id}: {e}")
                time.sleep(args.delay)
                continue
            for item in raw:
                p = item.get("player") or item
                pid = p.get("id")
                if pid is None:
                    continue
                name = (p.get("name") or "").strip() or None
                age = p.get("age")
                if age is not None and not isinstance(age, int):
                    try:
                        age = int(age)
                    except (TypeError, ValueError):
                        age = None
                nationality = (p.get("nationality") or "").strip() or None
                photo = (p.get("photo") or "").strip() or None
                position = None
                stats = item.get("statistics") or []
                if stats and isinstance(stats[0], dict):
                    games = (stats[0].get("games") or {}) if isinstance(stats[0], dict) else {}
                    position = (games.get("position") or "").strip() or None
                all_rows.append({
                    "id": int(pid),
                    "team_id": str(team_id),
                    "name": name,
                    "age": age,
                    "nationality": nationality,
                    "photo_url": photo,
                    "position": position,
                    "updated_at": now,
                })
            time.sleep(args.delay)
        time.sleep(0.3)

    if not all_rows:
        print("Aucun joueur récupéré.")
        return

    print(f"Total: {len(all_rows)} joueurs")
    if args.dry_run:
        print("Dry-run: pas d'écriture en base. Relance sans --dry-run pour importer.")
        return

    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    batch_size = 500
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i : i + batch_size]
        supabase.table("players").upsert(batch, on_conflict="id").execute()
        print(f"Upsert players {i + len(batch)}/{len(all_rows)}")
    print("Import joueurs terminé. Ne rappeler qu'en nouvelle saison.")


if __name__ == "__main__":
    main()
