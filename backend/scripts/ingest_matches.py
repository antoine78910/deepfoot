#!/usr/bin/env python3
"""
Script d'ingestion des matchs / résultats pour Visifoot 2.0.
Source: API football-data.org (v4) — https://www.football-data.org/
À lancer via cron (ex. 1×/jour) ou manuellement.

Usage:
  cd backend && python scripts/ingest_matches.py

Prérequis: .env avec FOOTBALL_DATA_API_TOKEN.
Optionnel: SUPABASE_URL + SUPABASE_KEY pour persister en base (results, teams, h2h).
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)


def main() -> None:
    from app.core.config import get_settings
    from app.services.football_data import (
        _use_api,
        get_matches,
        get_competition_teams,
        get_team_matches,
    )

    if not _use_api():
        print("football-data.org not configured. Set FOOTBALL_DATA_API_TOKEN in .env")
        print("Get a free token at https://www.football-data.org/client/register")
        return

    settings = get_settings()
    has_supabase = bool(settings.supabase_url and settings.supabase_key)

    # 1) Récupérer les matchs récents (ex: 30 derniers jours finis)
    date_to = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    matches = get_matches(date_from=date_from, date_to=date_to, status="FINISHED", limit=200)
    print(f"football-data.org: {len(matches)} matchs récupérés ({date_from} → {date_to})")

    if not matches:
        print("Aucun match trouvé pour la période. Vérifiez votre token et les compétitions accessibles.")
        return

    if has_supabase:
        from app.core.supabase_client import get_supabase
        supabase = get_supabase()
        teams_seen: set[str] = set()
        inserted = 0
        for m in matches:
            home = m.get("homeTeam") or {}
            away = m.get("awayTeam") or {}
            score = m.get("score") or {}
            ft = score.get("fullTime") or {}
            hid = str(home.get("id") or "")
            aid = str(away.get("id") or "")
            hname = (home.get("name") or "").strip()
            aname = (away.get("name") or "").strip()
            if not hid or not aid or not hname or not aname:
                continue
            hg = ft.get("homeTeam")
            ag = ft.get("awayTeam")
            if hg is None or ag is None:
                continue
            utc_date = (m.get("utcDate") or "")[:10]
            if not utc_date:
                continue
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
                    "home_goals": int(hg),
                    "away_goals": int(ag),
                    "date": utc_date,
                    "league": (m.get("competition") or {}).get("name"),
                },
            ).execute()
            inserted += 1
        print(f"Supabase: results et teams mis à jour ({inserted} nouveaux matchs).")
    else:
        print("Supabase non configuré: les matchs sont utilisables via l'API football-data uniquement (pas de persistance).")

    # 2) Optionnel: précharger les équipes de la compétition par défaut
    code = settings.football_data_default_competition
    teams = get_competition_teams(code)
    print(f"Compétition {code}: {len(teams)} équipes disponibles.")


if __name__ == "__main__":
    main()
