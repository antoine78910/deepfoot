# Visifoot 2.0

IA de prédiction de matchs de football : 1X2, Over/Under, BTTS, score exact. Style Visifoot, résumé et scénario via OpenAI.

## Stack

- **Backend** : Python, FastAPI, Poisson + XGBoost (ML)
- **DB** : Supabase (PostgreSQL + Auth)
- **Frontend** : Next.js (App Router), thème sombre

## Démarrage rapide

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # remplir SUPABASE_URL, SUPABASE_KEY, optionnel OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

- **Données matchs** : [football-data.org](https://www.football-data.org/) (v4). Token gratuit sur [client/register](https://www.football-data.org/client/register), variable `FOOTBALL_DATA_API_TOKEN` dans `backend/.env`. Les équipes sont cherchées dans **toutes les ligues** suivantes : WC, CL, BL1, DED, BSA, PD, FL1, ELC, PPL, EC, SA, PL (World Cup, Champions League, Bundesliga, Eredivisie, Brasileirão, Liga, Ligue 1, Championship, Primeira Liga, Euro, Serie A, Premier League). L’autocomplete sur la page d’accueil affiche les clubs avec **logo** (crest) dès que tu tapes (ex. « a » puis « aj » puis « aja » pour AJ Auxerre).
- Sans `.env` ou sans clés Supabase/OpenAI/football-data, l’API tourne en mode démo (données synthétiques, pas de résumé OpenAI).

### Frontend

```bash
cd frontend
npm install
# Créer .env.local avec NEXT_PUBLIC_API_URL=http://localhost:8000 si besoin
npm run dev
```

Ouvre http://localhost:3000 : saisir deux équipes → « Analyze the match with AI » → page résultat.

### Supabase

1. Créer un projet sur [supabase.com](https://supabase.com).
2. Exécuter les migrations dans `supabase/migrations/001_initial.sql` (SQL Editor).
3. Renseigner `SUPABASE_URL` et `SUPABASE_KEY` dans `backend/.env`.

## Documentation

- **Architecture complète** : [ARCHITECTURE.md](./ARCHITECTURE.md) (workflow, Poisson/XGBoost, abonnements, coûts).
- **Coût MVP** : [MVP_COST.md](./MVP_COST.md).

## Endpoints

| Méthode | URL | Description |
|--------|-----|-------------|
| POST | `/predict` | Body: `{ "home_team": "Lorient", "away_team": "Auxerre" }` → probas, xG, résumé |
| GET | `/teams?q= Lor` | Liste équipes (autocomplete) |
| GET | `/health` | Health check |
