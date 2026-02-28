# backend/app/schemas/predict.py
from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    home_team: str = Field(..., description="Nom ou slug équipe domicile")
    away_team: str = Field(..., description="Nom ou slug équipe extérieur")
    home_team_id: Optional[int] = Field(None, description="ID API équipe domicile (prioritaire si fourni)")
    away_team_id: Optional[int] = Field(None, description="ID API équipe extérieur (prioritaire si fourni)")
    use_api_predictions: bool = Field(False, description="Si True et fixture trouvée: 1X2 depuis API-Football Predictions au lieu du modèle Poisson")


class ExactScoreItem(BaseModel):
    home: int
    away: int
    probability: float


class OverUnderItem(BaseModel):
    line: str  # "0.5", "1.5", "2.5", "3.5"
    over_pct: float
    under_pct: float


class MostLikelyScoreItem(BaseModel):
    home: int
    away: int
    probability: float


class AsianHandicapItem(BaseModel):
    home_neg1_pct: float
    home_plus1_pct: float
    away_neg1_pct: float
    away_plus1_pct: float


class PredictResponse(BaseModel):
    home_team: str
    away_team: str
    league: Optional[str] = None
    match_date: Optional[str] = None
    venue: Optional[str] = None
    home_team_logo: Optional[str] = None
    away_team_logo: Optional[str] = None

    # Expected goals
    xg_home: float
    xg_away: float
    xg_total: float

    # 1X2
    prob_home: float
    prob_draw: float
    prob_away: float
    implied_odds_home: Optional[float] = None
    implied_odds_draw: Optional[float] = None
    implied_odds_away: Optional[float] = None

    # Score le plus probable
    most_likely_score: Optional[MostLikelyScoreItem] = None
    total_goals_distribution: Optional[dict[str, float]] = None  # {"0": pct, "1", "2", "3+"}
    goal_difference_dist: Optional[dict[str, float]] = None  # {"1", "2", "3+"}
    double_chance_1x: Optional[float] = None
    double_chance_x2: Optional[float] = None
    double_chance_12: Optional[float] = None
    asian_handicap: Optional[AsianHandicapItem] = None
    upset_probability: Optional[float] = None

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

    # API-Football Predictions (quand use_api_predictions=True)
    api_advice: Optional[str] = None

    # LLM
    quick_summary: Optional[str] = None
    scenario_1: Optional[str] = None
    scenario_2: Optional[dict] = None  # { title, body, probability_pct }
    scenario_3: Optional[dict] = None
    scenario_4: Optional[dict] = None
    key_forces_home: Optional[list[str]] = None
    key_forces_away: Optional[list[str]] = None
    ai_confidence: Optional[str] = None  # "Very high"

    # Stats comparatives (pour barres)
    attack_home_pct: Optional[float] = None
    defense_home_pct: Optional[float] = None
    form_home_pct: Optional[float] = None
    h2h_home_pct: Optional[float] = None
    goals_home_pct: Optional[float] = None
    overall_home_pct: Optional[float] = None
