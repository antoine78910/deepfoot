# backend/app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import predict, teams, competitions, leagues, webhooks, internal, me as me_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Visifoot 2.0 API",
    description="API de prédiction de matchs de football (1X2, Over/Under, BTTS, score exact)",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    # Local dev + Vercel preview/prod + production domain.
    # Note: CORSMiddleware does not support wildcard entries in allow_origins (like https://*.vercel.app).
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://app.localhost:3000",
        "http://app.127.0.0.1:3000",
        "https://deepfoot.io",
        "https://www.deepfoot.io",
        "https://app.deepfoot.io",
    ],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(predict.router)
app.include_router(teams.router)
app.include_router(leagues.router)
app.include_router(webhooks.router)
app.include_router(competitions.router)
app.include_router(internal.router)
app.include_router(me_router.router)


@app.on_event("startup")
def startup_whop_config():
    s = get_settings()
    whop_key = (s.whop_api_key or "").strip()
    company_id = (s.whop_company_id or "").strip()
    if whop_key:
        logger.info("WHOP_API_KEY: set (len=%d, prefix=%s)", len(whop_key), (whop_key[:8] + "…") if len(whop_key) >= 8 else "***")
    else:
        logger.warning("WHOP_API_KEY: not set (401 from Whop expected)")
    if company_id:
        logger.info("WHOP_COMPANY_ID: set (%s…)", (company_id[:10] + "…") if len(company_id) > 10 else company_id)
    else:
        logger.warning("WHOP_COMPANY_ID: not set")


@app.get("/")
def root():
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
