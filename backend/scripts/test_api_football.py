#!/usr/bin/env python3
"""Teste un appel API-Football pour diagnostiquer pourquoi l'ingest renvoie 0 match."""
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)

def main():
    from app.core.config import get_settings
    import httpx

    s = get_settings()
    key = (s.api_football_key or "").strip()
    if not key:
        print("API_FOOTBALL_KEY non chargé. Vérifiez .env ou .env.local dans le dossier backend.")
        return
    print(f"Clé chargée: {key[:4]}...{key[-4:] if len(key) > 8 else '****'}")

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": key, "Accept": "application/json"}
    params = {"league": 39, "season": 2025, "status": "FT"}  # Premier League

    print(f"GET {url}?league=39&season=2025&status=FT")
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=headers, params=params)
        print(f"Status: {r.status_code}")
        data = r.json() or {}
        print("Clés réponse:", list(data.keys()))
        if data.get("errors"):
            print("Erreurs API:", data["errors"])
        resp = data.get("response") or []
        print(f"Nombre de matchs (response): {len(resp)}")
        if resp:
            print("Exemple premier match (fixture.id, teams):", resp[0].get("fixture", {}).get("id"), resp[0].get("teams"))
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    main()
