#!/usr/bin/env python3
"""
Prépare toutes les données pour une analyse de match: équipes, 5 derniers matchs,
H2H, classement. Stocke dans Supabase avec cache 24h pour limiter les appels API.

Usage (depuis backend, venv activé):
  python scripts/prepare_match_analysis.py "Paris SG" "Marseille" 61
  python scripts/prepare_match_analysis.py "Liverpool" "Manchester United" 39 --force

Options:
  --force   Ignorer le cache et refaire tous les appels API.
"""
import argparse
import json
import os
import sys
from pathlib import Path

try:
    import pydantic_settings  # noqa: F401
except ImportError:
    print("Erreur: module 'pydantic_settings' introuvable. Lance le script avec le venv activé.")
    sys.exit(1)

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)


def main() -> None:
    from app.services.fetch_match_data import fetch_and_store

    parser = argparse.ArgumentParser(description="Prépare les données d'analyse pour un match (équipes, derniers matchs, H2H, classement).")
    parser.add_argument("home_team_name", help="Nom de l'équipe à domicile")
    parser.add_argument("away_team_name", help="Nom de l'équipe à l'extérieur")
    parser.add_argument("league_id", type=int, help="ID API-Football de la ligue (ex: 61 Ligue 1, 39 Premier League)")
    parser.add_argument("--force", action="store_true", help="Forcer le rafraîchissement (ignorer le cache 24h)")
    parser.add_argument("--json", action="store_true", help="Afficher le résultat brut en JSON")
    args = parser.parse_args()

    out = fetch_and_store(
        args.home_team_name.strip(),
        args.away_team_name.strip(),
        args.league_id,
        force_refresh=args.force,
    )

    if out.get("error"):
        print("Erreur:", out["error"])
        sys.exit(1)

    if args.json:
        # Sérialiser pour JSON (tuple h2h -> list, datetime éventuels)
        d = dict(out)
        d["h2h"] = list(d["h2h"])
        print(json.dumps(d, indent=2, default=str))
        return

    teams = out.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    h2h = out.get("h2h") or (0, 0, 0)
    print("Match:", home.get("name", "?"), "–", away.get("name", "?"))
    print("IDs:", out.get("home_team_id"), "–", out.get("away_team_id"))
    print("Derniers matchs domicile:", len(out.get("last_5_home") or []))
    print("Derniers matchs extérieur:", len(out.get("last_5_away") or []))
    print("H2H (D-N-E):", h2h[0], "-", h2h[1], "-", h2h[2])
    print("Lignes classement:", len(out.get("standings") or []))
    print("Données prêtes pour l'analyse (stockées en base si Supabase configuré).")


if __name__ == "__main__":
    main()
