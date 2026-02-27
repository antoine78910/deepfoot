# backend/app/core/leagues.py
"""
Ligues supportées — IDs API-Football (https://www.api-football.com/documentation-v3).
Utilisées pour l'autocomplete et la résolution des noms d'équipes.
"""
from typing import TypedDict


class League(TypedDict):
    id: int
    name: str


# ID = league id API-Football (numérique). Plus il y a de ligues, plus la recherche/suggestion couvre d'équipes.
LEAGUES: list[League] = [
    # Coupes
    {"id": 1, "name": "World Cup"},
    {"id": 2, "name": "UEFA Champions League"},
    {"id": 3, "name": "UEFA Europa League"},
    {"id": 4, "name": "European Championship"},
    # France
    {"id": 61, "name": "Ligue 1"},
    {"id": 62, "name": "Ligue 2"},
    # Espagne
    {"id": 140, "name": "La Liga"},
    {"id": 141, "name": "Segunda División"},
    # Allemagne
    {"id": 78, "name": "Bundesliga"},
    {"id": 79, "name": "2. Bundesliga"},
    # Italie
    {"id": 135, "name": "Serie A"},
    {"id": 136, "name": "Serie B"},
    # Angleterre
    {"id": 39, "name": "Premier League"},
    {"id": 40, "name": "Championship"},
    {"id": 41, "name": "League One"},
    # Belgique
    {"id": 144, "name": "Jupiler Pro League"},
    {"id": 145, "name": "Challenger Pro League"},
    # Pays-Bas
    {"id": 88, "name": "Eredivisie"},
    {"id": 89, "name": "Eerste Divisie"},
    # Portugal
    {"id": 94, "name": "Primeira Liga"},
    {"id": 96, "name": "Liga Portugal 2"},
    # Turquie
    {"id": 203, "name": "Süper Lig"},
    {"id": 204, "name": "1. Lig"},
    # Suisse / Arabie Saoudite
    {"id": 207, "name": "Super League"},
    {"id": 307, "name": "Pro League"},  # Saudi Arabia
    # Autres
    {"id": 71, "name": "Serie A Brasil"},
    {"id": 266, "name": "Botola Pro"},
]
LEAGUE_IDS: list[int] = [L["id"] for L in LEAGUES]

# Saison courante au sens API-Football : année de *début* de la saison (ex: 2025 = 2025-26).
# En Europe la saison commence en août ; avant août on est encore dans la saison N-1.
def current_season() -> int:
    from datetime import datetime
    now = datetime.now()
    if now.month >= 8:
        return now.year
    return now.year - 1


