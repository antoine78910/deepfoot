#!/usr/bin/env python3
"""
Synchronise toutes les équipes (clubs + sélections) vers Supabase par pays.
Utilise GET /teams?country={CountryName} pour chaque pays (documentation API-Football v3).
Inclut les blasons (logo_url) et search_terms pour la recherche/suggestion.

Prérequis:
  - .env avec API_FOOTBALL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY (ou SUPABASE_KEY)
  - Table teams avec colonnes: slug (text, PK), name, logo_url, search_terms (text), last_updated

Usage:
  cd backend && .\\venv\\Scripts\\python.exe scripts/sync_teams_by_country_to_supabase.py
  # Limiter aux pays européens (moins d'appels API):
  cd backend && .\\venv\\Scripts\\python.exe scripts/sync_teams_by_country_to_supabase.py --only Europe
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


def _build_search_terms(name: str) -> str:
    """Construit search_terms : nom normalisé + alias (psg, aja, om...)."""
    from app.services.api_football import _normalize_for_search, TEAM_SEARCH_ALIASES
    n = _normalize_for_search(name or "")
    parts = [n] if n else []
    for alias_key, alias_parts in TEAM_SEARCH_ALIASES.items():
        if any(p in n for p in alias_parts):
            parts.append(alias_key)
    return ",".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync all teams (by country) to Supabase with logos.")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Limiter à des pays: noms séparés par des virgules (ex: France,Belgium,Spain). Sans ce flag = tous les pays.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.8,
        help="Délai en secondes entre chaque requête pays (éviter rate limit). Défaut 1.8.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne pas écrire dans Supabase, seulement lister pays et nombre d'équipes.",
    )
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.services.api_football import _use_api, get_countries, get_teams_by_country

    settings = get_settings()
    if not _use_api():
        print("API_FOOTBALL_KEY manquant dans .env")
        sys.exit(1)
    if not args.dry_run and not (settings.supabase_url and settings.supabase_key):
        print("SUPABASE_URL et SUPABASE_KEY (ou SUPABASE_SERVICE_KEY) requis.")
        sys.exit(1)

    countries = get_countries()
    if not countries:
        print("Aucun pays récupéré. Vérifiez l'API (GET /countries).")
        sys.exit(1)

    # Filtre optionnel: liste de noms de pays (séparés par des virgules)
    if args.only:
        only_names = {s.strip().lower() for s in args.only.split(",") if s.strip()}
        countries = [c for c in countries if (c.get("name") or "").strip().lower() in only_names]
        if not countries:
            print(f"Aucun pays trouvé pour: {args.only}")
            sys.exit(1)

    print(f"Pays à traiter: {len(countries)}")
    if args.dry_run:
        total_teams = 0
        for c in countries:
            name = c.get("name") or ""
            teams = get_teams_by_country(name)
            total_teams += len(teams)
            print(f"  {name}: {len(teams)} équipes")
            time.sleep(args.delay)
        print(f"Total: {total_teams} équipes. Relance sans --dry-run pour écrire dans Supabase.")
        return

    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    seen_ids = set()
    all_rows = []

    for i, country in enumerate(countries):
        country_name = (country.get("name") or "").strip()
        if not country_name:
            continue
        try:
            items = get_teams_by_country(country_name)
        except Exception as e:
            print(f"  [{country_name}] Erreur: {e}")
            time.sleep(args.delay)
            continue
        added = 0
        for item in items:
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
            all_rows.append({
                "slug": str(tid),
                "name": name,
                "logo_url": logo,
                "search_terms": search_terms,
                "country": country_name,
                "last_updated": now,
            })
            added += 1
        print(f"  [{i+1}/{len(countries)}] {country_name}: {len(items)} équipes ({added} nouvelles)")
        time.sleep(args.delay)

    if not all_rows:
        print("Aucune équipe à insérer.")
        return

    batch_size = 500
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i : i + batch_size]
        supabase.table("teams").upsert(batch, on_conflict="slug").execute()
        print(f"Upsert {len(batch)} équipes ({i + len(batch)}/{len(all_rows)})")

    print(f"Terminé: {len(all_rows)} équipes en base (tous pays, blasons inclus). La suggestion utilisera Supabase.")


if __name__ == "__main__":
    main()
