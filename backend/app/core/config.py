# backend/app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    openai_api_key: str = ""
    free_analyses_per_day: int = 1
    max_score_goals: int = 8  # grille Poisson 0..8
    # football-data.org (https://www.football-data.org/)
    football_data_api_token: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"
    football_data_default_competition: str = "FL1"  # Ligue 1 pour résolution des noms d'équipes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
