# backend/app/schemas/predict.py
from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    home_team: str = Field(..., description="Nom ou slug équipe domicile")
    away_team: str = Field(..., description="Nom ou slug équipe extérieur")


class ExactScoreItem(BaseModel):
    home: int
    away: int
    probability: float


class OverUnderItem(BaseModel):
    line: str  # "0.5", "1.5", "2.5", "3.5"
    over_pct: float
    under_pct: float


class PredictResponse(BaseModel):
    home_team: str
    away_team: str
    league: Optional[str] = None
    match_date: Optional[str] = None
    venue: Optional[str] = None

    # Expected goals
    xg_home: float
    xg_away: float
    xg_total: float

    # 1X2
    prob_home: float
    prob_draw: float
    prob_away: float

    # BTTS
    btts_yes_pct: float
    btts_no_pct: float

    # Over/Under (0.5, 1.5, 2.5, 3.5)
    over_under: list[OverUnderItem]

    # Top score exact
    exact_scores: list[ExactScoreItem]

    # Form & H2H (pour affichage)
    home_form: Optional[list[str]] = None  # ["W","D","L","W","W"]
    away_form: Optional[list[str]] = None
    home_wdl: Optional[str] = None  # "3-1-1"
    away_wdl: Optional[str] = None
    home_form_label: Optional[str] = None  # "Great form"
    away_form_label: Optional[str] = None  # "Poor form"

    # LLM
    quick_summary: Optional[str] = None
    scenario_1: Optional[str] = None
    ai_confidence: Optional[str] = None  # "Very high"

    # Stats comparatives (pour barres)
    attack_home_pct: Optional[float] = None
    defense_home_pct: Optional[float] = None
    form_home_pct: Optional[float] = None
    h2h_home_pct: Optional[float] = None
    goals_home_pct: Optional[float] = None
    overall_home_pct: Optional[float] = None
