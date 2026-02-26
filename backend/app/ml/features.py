# backend/app/ml/features.py
"""
Feature engineering pour un match : last 5-10 matchs, home/away, H2H.
Les données sont supposées venir de Supabase (matches, results, h2h).
"""
from typing import Optional
import math


def compute_goals_avg(goals_for: list[int], goals_against: list[int], default: float = 1.2) -> tuple[float, float]:
    """Moyenne buts marqués et encaissés. Retourne (avg_for, avg_against)."""
    if not goals_for and not goals_against:
        return (default, default)
    n = max(len(goals_for), len(goals_against), 1)
    avg_for = sum(goals_for) / n if goals_for else default
    avg_against = sum(goals_against) / n if goals_against else default
    return (avg_for, avg_against)


def form_to_wdl(form: list[str]) -> str:
    """['W','D','L','W','W'] -> '3-1-1'."""
    w = sum(1 for x in form if x.upper() == "W")
    d = sum(1 for x in form if x.upper() == "D")
    l = sum(1 for x in form if x.upper() == "L")
    return f"{w}-{d}-{l}"


def form_to_label(wins: int, draws: int, losses: int) -> str:
    """Label global form : Great form / Average / Poor form."""
    total = wins + draws + losses or 1
    pts = wins * 3 + draws
    ratio = pts / (total * 3)
    if ratio >= 0.6:
        return "Great form"
    if ratio >= 0.4:
        return "Average form"
    return "Poor form"


def compute_lambda_home_away(
    home_goals_for: list[int],
    home_goals_against: list[int],
    away_goals_for: list[int],
    away_goals_against: list[int],
    league_avg_goals: float = 2.7,
) -> tuple[float, float]:
    """
    Calcule les forces d'attaque/défense et en déduit lambda_home et lambda_away
    pour le modèle de Poisson (approche Dixon-Robinson simplifiée).
    """
    default = max(league_avg_goals / 2, 1.0)
    h_for, h_against = compute_goals_avg(home_goals_for, home_goals_against, default)
    a_for, a_against = compute_goals_avg(away_goals_for, away_goals_against, default)

    # Force attaque = buts marqués, force défense = buts encaissés
    # lambda_home = attaque_home * défense_away / league_avg
    league_avg_half = league_avg_goals / 2
    lambda_home = (h_for * a_against) / league_avg_half if league_avg_half else h_for
    lambda_away = (a_for * h_against) / league_avg_half if league_avg_half else a_for

    # Lisser pour éviter extrêmes
    lambda_home = max(0.2, min(4.0, lambda_home))
    lambda_away = max(0.2, min(4.0, lambda_away))
    return (lambda_home, lambda_away)


def pct_from_form(wins: int, draws: int, losses: int) -> float:
    """Pourcentage 'form' pour barre (0-100)."""
    total = wins + draws + losses or 1
    pts = wins * 3 + draws
    return (pts / (total * 3)) * 100


def build_comparison_pcts(
    home_w: int, home_d: int, home_l: int,
    away_w: int, away_d: int, away_l: int,
    home_goals_for: float, away_goals_for: float,
    home_goals_against: float, away_goals_against: float,
    h2h_home_w: int = 0, h2h_draw: int = 0, h2h_away_w: int = 0,
) -> dict[str, float]:
    """Retourne les pourcentages pour les barres (attack, defense, form, h2h, goals, overall)."""
    total_h2h = h2h_home_w + h2h_draw + h2h_away_w or 1
    h2h_home_pct = (h2h_home_w + 0.5 * h2h_draw) / total_h2h * 100

    form_home_pct = pct_from_form(home_w, home_d, home_l)
    form_away_pct = pct_from_form(away_w, away_d, away_l)
    form_total = form_home_pct + form_away_pct or 1
    form_home_pct = form_home_pct / form_total * 100

    attack_home = home_goals_for
    attack_away = away_goals_for
    attack_total = attack_home + attack_away or 1
    attack_home_pct = (attack_home / attack_total) * 100

    def_home = 1.0 / (home_goals_against or 0.5)
    def_away = 1.0 / (away_goals_against or 0.5)
    def_total = def_home + def_away or 1
    defense_home_pct = (def_home / def_total) * 100

    goals_home = home_goals_for
    goals_away = away_goals_for
    goals_total = goals_home + goals_away or 1
    goals_home_pct = (goals_home / goals_total) * 100

    overall_home_pct = (
        attack_home_pct + defense_home_pct + form_home_pct + h2h_home_pct + goals_home_pct
    ) / 5.0

    return {
        "attack_home_pct": round(attack_home_pct, 0),
        "defense_home_pct": round(defense_home_pct, 0),
        "form_home_pct": round(form_home_pct, 0),
        "h2h_home_pct": round(h2h_home_pct, 0),
        "goals_home_pct": round(goals_home_pct, 0),
        "overall_home_pct": round(overall_home_pct, 0),
    }
