# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field, model_validator


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    # Optionnel : clé service_role pour mettre à jour profiles.plan depuis le webhook Whop (recherche user par email)
    supabase_service_role_key: str = ""
    openai_api_key: str = ""
    free_analyses_per_day: int = 1
    max_score_goals: int = 8  # grille Poisson 0..8
    # API-Football (https://www.api-football.com/documentation-v3) — legacy, utilisé si Sportmonks non configuré
    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"
    # Sportmonks Football API v3 (https://docs.sportmonks.com/v3/) — nouveau modèle data + prédictions
    # Lit SPORTMONKS_API_TOKEN ou, à défaut, API_FOOTBALL_KEY (même clé possible côté user)
    sportmonks_api_token: str = ""
    admin_api_key: str = ""  # Si défini, requiert X-Admin-Key pour /admin/*
    admin_dashboard_token: str = "Zjhfc82005??"  # Token simple pour /internal/admin/* (dashboard interne)
    # Polling matchs terminés (FT) : intervalle en secondes (10 = test, 3600 = 1h)
    polling_interval_seconds: int = 10
    # NewsAPI.org (optionnel) — actualités pour le quick summary style Visifoot
    news_api_key: str = ""
    # DataFast — attribution des revenus (Payment API)
    datafast_api_key: str = ""
    # Whop — secret du webhook pour vérifier la signature (ws_...)
    whop_webhook_secret: str = ""
    # Whop — API key (Company API key from Whop Dashboard; env: WHOP_API_KEY)
    whop_api_key: str = Field(default="", validation_alias="WHOP_API_KEY")
    # Whop — Company ID (biz_xxx) pour annulation par email si pas de membership_id; env: WHOP_COMPANY_ID
    whop_company_id: str = Field(default="", validation_alias="WHOP_COMPANY_ID")
    # Notification offre fidélité (claim 50%) : envoi email à notify_offer_email si RESEND_API_KEY est défini
    resend_api_key: str = ""
    notify_offer_email: str = "anto.delbos@gmail.com"
    notify_from_email: str = "DeepFoot <onboarding@resend.dev>"  # Doit être un domaine vérifié Resend en prod

    @model_validator(mode="before")
    @classmethod
    def inject_env_fallbacks(cls, data: dict) -> dict:
        """Injecte les fallbacks env avant construction pour éviter model_copy (warning Pydantic)."""
        if not isinstance(data, dict):
            return data
        # Sportmonks : depuis .env.local (api_football_key) ou SPORTMONKS_API_TOKEN / API_FOOTBALL_KEY
        token = (data.get("sportmonks_api_token") or data.get("api_football_key") or "").strip()
        if not token:
            token = (os.getenv("API_FOOTBALL_KEY") or os.getenv("SPORTMONKS_API_TOKEN") or "").strip()
        if token:
            data["sportmonks_api_token"] = token
        # Supabase : NEXT_PUBLIC_* / SUPABASE_* si url/key vides
        url = (data.get("supabase_url") or "").strip()
        if not url:
            url = (os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").strip()
        if url:
            data["supabase_url"] = url
        key = (data.get("supabase_key") or "").strip()
        if not key:
            key = (
                os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
                or os.getenv("SUPABASE_ANON_KEY")
                or os.getenv("SUPABASE_KEY")
                or ""
            ).strip()
        if key:
            data["supabase_key"] = key
        return data

    class Config:
        # .env.local override .env (secrets locaux sans les commiter)
        env_file = [".env", ".env.local"]
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
