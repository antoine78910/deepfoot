# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import predict, teams, competitions

app = FastAPI(
    title="Visifoot 2.0 API",
    description="API de prédiction de matchs de football (1X2, Over/Under, BTTS, score exact)",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(predict.router)
app.include_router(teams.router)
app.include_router(competitions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
