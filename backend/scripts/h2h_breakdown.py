#!/usr/bin/env python3
"""
Breakdown H2H (head-to-head) entre deux équipes par saison.
Idéal : 3 dernières saisons. Max : 5 saisons avec pondération (matchs récents plus pertinents).

Usage:
  cd backend
  python scripts/h2h_breakdown.py "Lorient" "Auxerre"
  python scripts/h2h_breakdown.py "Lorient" "Auxerre" --max-seasons 5 --ideal-seasons 3

Prérequis: API_FOOTBALL_KEY dans .env
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)


def season_from_date(date_str: str) -> int:
    """Saison européenne : août → année civile de début. Ex: 2024-03-15 → 2023 (saison 2023/24)."""
    if not date_str:
        return 0
    try:
        y = int(date_str[:4])
        m = int(date_str[5:7]) if len(date_str) >= 7 else 1
        return y if m >= 8 else y - 1
    except (ValueError, TypeError):
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="H2H breakdown entre deux équipes (3–5 saisons, pondéré)")
    parser.add_argument("team1", help="Nom équipe 1 (ex. Lorient)")
    parser.add_argument("team2", help="Nom équipe 2 (ex. Auxerre)")
    parser.add_argument("--max-seasons", type=int, default=5, help="Nombre max de saisons à inclure (défaut: 5)")
    parser.add_argument("--ideal-seasons", type=int, default=3, help="Nombre de saisons 'idéal' pour résumé (défaut: 3)")
    parser.add_argument("--weighted", action="store_true", default=True, help="Pondérer par ancienneté (récent = plus lourd)")
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.services.api_football import (
        _use_api,
        resolve_team_name_to_id,
        get_fixtures_headtohead,
    )

    if not _use_api():
        print("API-Football non configurée. Définir API_FOOTBALL_KEY.")
        sys.exit(1)

    t1_id = resolve_team_name_to_id(args.team1.strip())
    t2_id = resolve_team_name_to_id(args.team2.strip())
    if not t1_id or not t2_id:
        print(f"Équipe(s) introuvable(s): '{args.team1}' / '{args.team2}'")
        sys.exit(1)

    team1_id, team2_id = t1_id, t2_id
    fixtures = get_fixtures_headtohead(team1_id, team2_id, last_n=50)
    if not fixtures:
        print(f"Aucun match H2H trouvé entre {args.team1} et {args.team2}.")
        sys.exit(0)

    # Grouper par saison (année de début de saison)
    by_season: dict[int, list[dict]] = defaultdict(list)
    for f in fixtures:
        fix = f.get("fixture") or {}
        date_val = fix.get("date") or ""
        season = season_from_date(date_val)
        if season:
            by_season[season].append(f)

    seasons_sorted = sorted(by_season.keys(), reverse=True)
    # Limiter à max_seasons
    seasons_sorted = seasons_sorted[: args.max_seasons]
    ideal_seasons = seasons_sorted[: args.ideal_seasons]

    # Poids par ancienneté : saison la plus récente = 1.0, puis décroissant
    # index 0 = plus récent → weight 1.0, 0.8, 0.6, 0.4, 0.2
    def weight_for_index(i: int) -> float:
        if not args.weighted:
            return 1.0
        return max(0.2, 1.0 - 0.2 * i)

    print("=" * 60)
    print(f"H2H: {args.team1} vs {args.team2}")
    print("=" * 60)

    total_h_wins = total_draws = total_a_wins = 0
    total_h_goals = total_a_goals = 0
    weighted_h = weighted_d = weighted_a = 0.0
    total_weight = 0.0

    for idx, season in enumerate(seasons_sorted):
        matches = by_season[season]
        w = weight_for_index(idx)
        h_wins = draws = a_wins = 0
        h_goals = a_goals = 0
        lines = []
        for m in matches:
            teams = m.get("teams") or {}
            goals = m.get("goals") or {}
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            hid = home.get("id")
            hg = int(goals.get("home") if goals.get("home") is not None else 0)
            ag = int(goals.get("away") if goals.get("away") is not None else 0)
            h_name = (home.get("name") or "").strip()
            a_name = (away.get("name") or "").strip()
            fix = m.get("fixture") or {}
            date_str = (fix.get("date") or "")[:10]
            # team1 = première équipe (args.team1), team2 = deuxième (args.team2)
            if hid == team1_id:
                # team1 à domicile
                h_goals += hg
                a_goals += ag
                if hg > ag:
                    h_wins += 1
                elif hg < ag:
                    a_wins += 1
                else:
                    draws += 1
                lines.append(f"  {date_str}  {h_name} {hg}-{ag} {a_name}")
            else:
                # team2 à domicile
                h_goals += ag
                a_goals += hg
                if ag > hg:
                    h_wins += 1
                elif ag < hg:
                    a_wins += 1
                else:
                    draws += 1
                lines.append(f"  {date_str}  {a_name} {hg}-{ag} {h_name}")

        total_h_wins += h_wins
        total_draws += draws
        total_a_wins += a_wins
        total_h_goals += h_goals
        total_a_goals += a_goals
        weighted_h += h_wins * w
        weighted_d += draws * w
        weighted_a += a_wins * w
        total_weight += (h_wins + draws + a_wins) * w

        label = " (idéal)" if season in ideal_seasons else ""
        print(f"\n--- Saison {season}/{str(season+1)[-2:]}{label} ({len(matches)} matchs, poids={w:.1f}) ---")
        print(f"  Victoires {args.team1}: {h_wins}  |  Nuls: {draws}  |  Victoires {args.team2}: {a_wins}")
        print(f"  Buts: {h_goals} - {a_goals}")
        for line in lines:
            print(line)

    print("\n" + "=" * 60)
    print("RÉSUMÉ GLOBAL (toutes saisons chargées)")
    print("=" * 60)
    n = total_h_wins + total_draws + total_a_wins
    print(f"Total matchs: {n}")
    print(f"Victoires {args.team1}: {total_h_wins}  |  Nuls: {total_draws}  |  Victoires {args.team2}: {total_a_wins}")
    print(f"Buts: {total_h_goals} - {total_a_goals}")

    if args.weighted and total_weight > 0:
        print("\n--- Avec pondération (récent = plus lourd) ---")
        wh = weighted_h / total_weight * 100
        wd = weighted_d / total_weight * 100
        wa = weighted_a / total_weight * 100
        print(f"  Victoires {args.team1}: {wh:.1f}%  |  Nuls: {wd:.1f}%  |  Victoires {args.team2}: {wa:.1f}%")

    if ideal_seasons:
        print("\n--- Résumé 3 dernières saisons (idéal) ---")
        ih = idraw = ia = ig_h = ig_a = 0
        for s in ideal_seasons:
            for m in by_season[s]:
                teams = m.get("teams") or {}
                goals = m.get("goals") or {}
                home = teams.get("home") or {}
                hid = home.get("id")
                hg = int(goals.get("home") if goals.get("home") is not None else 0)
                ag = int(goals.get("away") if goals.get("away") is not None else 0)
                if hid == team1_id:
                    ig_h += hg
                    ig_a += ag
                    if hg > ag:
                        ih += 1
                    elif hg < ag:
                        ia += 1
                    else:
                        idraw += 1
                else:
                    ig_h += ag
                    ig_a += hg
                    if ag > hg:
                        ih += 1
                    elif ag < hg:
                        ia += 1
                    else:
                        idraw += 1
        in_ = ih + idraw + ia
        if in_:
            print(f"  Matchs: {in_}  |  {args.team1} {ih} / Nuls {idraw} / {args.team2} {ia}  |  Buts: {ig_h}-{ig_a}")


if __name__ == "__main__":
    main()
