# backend/app/core/leagues.py
"""
Ligues supportées (codes football-data.org v4).
Utilisées pour l'autocomplete et la résolution des noms d'équipes.
"""
from typing import TypedDict


class League(TypedDict):
    code: str
    name: str


# Toutes les ligues à inclure (autocomplete + résolution équipes)
LEAGUES: list[League] = [
    {"code": "WC", "name": "FIFA World Cup"},
    {"code": "CL", "name": "UEFA Champions League"},
    {"code": "BL1", "name": "Bundesliga"},
    {"code": "DED", "name": "Eredivisie"},
    {"code": "BSA", "name": "Campeonato Brasileiro Série A"},
    {"code": "PD", "name": "Primera Division"},
    {"code": "FL1", "name": "Ligue 1"},
    {"code": "ELC", "name": "Championship"},
    {"code": "PPL", "name": "Primeira Liga"},
    {"code": "EC", "name": "European Championship"},
    {"code": "SA", "name": "Serie A"},
    {"code": "PL", "name": "Premier League"},
]

LEAGUE_CODES: list[str] = [L["code"] for L in LEAGUES]
