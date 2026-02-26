# Visifoot 2.0 — Architecture & plan de développement

## 1. Vue d’ensemble

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VISIFOOT 2.0 — FLUX GLOBAL                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   [Cron / Cursor]     [Supabase]        [Backend Python]      [Next.js]          │
│        │                   │                    │                  │            │
│        ▼                   ▼                    ▼                  ▼            │
│   Ingestion data  ──►  PostgreSQL   ◄──  FastAPI + ML   ◄──  Frontend MVP       │
│   (matches, H2H)       (teams,       │   /predict,           (analyse match,     │
│                        results)      │   /teams, auth)        abo 1/jour)       │
│                             │        │         │                               │
│                             └────────┴─────────┘                               │
│                                  Auth (Supabase)                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stack technique

| Composant | Techno | Rôle |
|-----------|--------|------|
| **Backend / API** | Python 3.11+, FastAPI | Endpoints REST, orchestration ML, règles métier |
| **ML** | Poisson (score exact), XGBoost (1X2, O/U, BTTS) | Prédictions à partir des features |
| **Base de données** | Supabase (PostgreSQL + Auth) | Teams, matchs, résultats, H2H, abonnements, usage |
| **Frontend** | Next.js (App Router) | Page match, formulaire équipes, affichage résultats style Visifoot |
| **Orchestration data** | Scripts Python + cron (ou Cursor) | Mise à jour données (derniers matchs, H2H) |
| **Résumé / scénarios** | OpenAI API (optionnel MVP) | Quick summary + Scenario #1 (texte) |

---

## 3. Workflow de bout en bout

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  1. INGESTION    │    │  2. FEATURE      │    │  3. ML           │
│  Données brutes  │───►│  ENGINEERING     │───►│  Prédictions     │
│  (API football,  │    │  (last 5–10,      │    │  Poisson +       │
│   scrap, CSV)    │    │   home/away, H2H) │    │  XGBoost         │
└──────────────────┘    └──────────────────┘    └────────┬─────────┘
        │                           │                      │
        ▼                           ▼                      ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Supabase        │    │  Vecteur par      │    │  xG home/away,    │
│  tables:         │    │  match (home_goals_│    │  P(1), P(X), P(2),│
│  teams, matches, │    │  avg, away_goals_ │    │  Over/Under,      │
│  results, h2h    │    │  avg, form_*, …   │    │  BTTS, score grid │
└──────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. API FastAPI                                                      │
│  POST /predict { home_team, away_team }                              │
│  → Vérif abo (1/jour vs illimité)                                   │
│  → Chargement features depuis Supabase                               │
│  → Appel modèles → JSON (probas, xG, scénarios)                     │
│  → (Optionnel) Appel OpenAI pour résumé + scenario #1                │
└─────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. Frontend Next.js                                                 │
│  Page 1 : Saisie équipes (style image 1 — fond sombre, gradient)    │
│  Page 2 : Résultat analyse (style image 2 — cartes, form, résumé)   │
│  Affichage : 1X2, Over/Under, BTTS, xG, score exact, résumé AI       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Combinaison Poisson + XGBoost

### 4.1 Rôle du modèle de Poisson

- **Entrées :** expected goals λ_home, λ_away (dérivés des buts marqués/encaissés sur last N matchs, home/away).
- **Sortie :** grille de probabilités pour chaque score (i, j) :  
  `P(score = i-j) = Poisson(i | λ_home) × Poisson(j | λ_away)` (indépendance des buts).
- **Utilisation :**
  - **Score exact** : proba max ou top-5 scores.
  - **xG affichés** : λ_home, λ_away.
  - **Over/Under** : somme des P(i,j) pour i+j &gt; k (ex. Over 2.5).
  - **BTTS** : somme des P(i,j) pour i ≥ 1 et j ≥ 1.

### 4.2 Rôle de XGBoost

- **Entrées :** mêmes features que pour Poisson (form, home/away, H2H, buts pour/contre, etc.) + éventuellement xG dérivés.
- **Sorties (classif / régression) :**
  - **1X2** : 3 classes (Home / Draw / Away) → P(1), P(X), P(2).
  - **Over/Under 2.5** : binaire → P(Over 2.5), P(Under 2.5).
  - **BTTS** : binaire → P(BTTS Yes), P(BTTS No).

### 4.3 Combinaison dans l’API

```
Features (Supabase + calculs)
        │
        ├──────────────────────────────┬──────────────────────────────┐
        ▼                              ▼                              ▼
  [Poisson model]               [XGBoost 1X2]               [XGBoost O/U, BTTS]
  λ_home, λ_away                P(1), P(X), P(2)            P(Over2.5), P(BTTS)
        │                              │                              │
        └──────────────────────────────┴──────────────────────────────┘
                                        │
                                        ▼
                    Réponse /predict : { exact_score, 1x2, over_under, btts, xg }
```

- **MVP :** on peut utiliser **uniquement Poisson** pour 1X2, O/U, BTTS (en dérivant tout depuis la grille de scores) pour simplifier. Ensuite on ajoute XGBoost pour affiner 1X2 et O/U si besoin.

---

## 5. Limitation des analyses : 1/jour vs illimité

### 5.1 Modèle de données (Supabase)

- **profiles** (ou `subscriptions`) : `user_id`, `plan` (`free` | `premium`), `analyses_used_today`, `last_analysis_date`.
- **analysis_log** : `user_id`, `match_id` ou `home_team_id`, `away_team_id`, `created_at` (pour déduplication et stats).

### 5.2 Règles

| Plan | Analyses / jour | Reset |
|------|------------------|--------|
| **free** | 1 | Minuit UTC (ou timezone config) |
| **premium** | Illimité | — |

### 5.3 Logique dans FastAPI

1. Après auth Supabase, récupérer `plan` et `analyses_used_today`, `last_analysis_date`.
2. Si `plan == 'free'` :
   - Si `last_analysis_date < today` → réinitialiser `analyses_used_today = 0`, `last_analysis_date = today`.
   - Si `analyses_used_today >= 1` → retourner `403` + message « 1 analyse gratuite par jour ».
3. Incrémenter `analyses_used_today` et mettre à jour `last_analysis_date` après une prédiction réussie.
4. Logger dans `analysis_log` pour audit.

---

## 6. Plan ultra-low-cost MVP (~0–10 €/mois)

| Poste | Choix low-cost | Coût indicatif |
|-------|----------------|----------------|
| **Hébergement API** | Render free / Fly.io free / Railway 5$/mois | 0–5 € |
| **Frontend** | Vercel free | 0 € |
| **Base de données** | Supabase free tier (500 Mo, 2 projets) | 0 € |
| **Auth** | Supabase Auth (inclus) | 0 € |
| **Données matchs** | API gratuite (ex. API-Football free tier, ou CSV open data) | 0 € |
| **OpenAI** | Résumé + scenario : 1 appel par analyse, modèle pas cher (gpt-4o-mini) | ~0,01 € / analyse |
| **Cron** | cron-job.org / GitHub Actions (gratuit) ou Cursor manuel | 0 € |

**Optimisations :**

- Cache des prédictions par (home_team, away_team, date) pour éviter de recalculer à chaque fois.
- Entraînement XGBoost/Poisson local ou sur un job hebdo (pas de serveur ML dédié).
- Limiter les appels OpenAI : résumé uniquement si pas déjà en cache pour ce match.
- Utiliser un seul projet Supabase et des RLS pour sécuriser les données par user.

---

## 7. Composants et rôles

```
visifoot-2.0/
├── backend/                 # FastAPI + ML
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, routes
│   │   ├── api/
│   │   │   ├── predict.py   # POST /predict, limite abo
│   │   │   └── teams.py     # GET /teams (autocomplete)
│   │   ├── core/
│   │   │   ├── config.py    # Settings (Supabase, OpenAI)
│   │   │   └── supabase.py  # Client Supabase
│   │   ├── ml/
│   │   │   ├── features.py  # Feature engineering (last 5–10, H2H, home/away)
│   │   │   ├── poisson.py   # Modèle Poisson, xG, score exact, O/U, BTTS
│   │   │   └── xgboost_models.py  # 1X2, O/U, BTTS (optionnel)
│   │   ├── services/
│   │   │   ├── subscription.py  # Vérif 1/jour vs illimité
│   │   │   └── openai_summary.py # Résumé + scenario #1
│   │   └── schemas/
│   │       └── predict.py   # Pydantic request/response
│   ├── scripts/
│   │   └── ingest_matches.py  # Cron : mise à jour données
│   └── requirements.txt
│
├── frontend/                # Next.js
│   ├── app/
│   │   ├── page.tsx         # Landing / formulaire match (style image 1)
│   │   ├── analysis/[id].tsx  # Résultat analyse (style image 2)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── MatchInput.tsx   # Deux champs équipes + logos + bouton
│   │   ├── AnalysisResult.tsx # Cartes form, résumé, scénarios, 1X2, O/U, BTTS
│   │   └── ...
│   └── package.json
│
├── supabase/
│   └── migrations/         # Tables teams, matches, results, h2h, profiles
│
└── ARCHITECTURE.md         # Ce fichier
```

---

## 8. Étapes pour commencer le développement

1. **Supabase** : créer projet, noter URL + anon key. Créer tables (teams, matches, results, h2h, profiles, analysis_log) + RLS.
2. **Backend** : `python -m venv venv`, `pip install fastapi uvicorn supabase xgboost scipy pandas`, implémenter `features.py` et `poisson.py`, puis `POST /predict` (sans auth d’abord pour tester).
3. **Limite abo** : implémenter `subscription.py` et l’appeler dans `predict.py` dès que l’auth est en place.
4. **Frontend** : `npx create-next-app`, reproduire le style des images (fond sombre, cartes, gradient cyan/vert), formulaire équipes → appel `/predict` → page résultat avec tous les blocs (form, résumé, scénario, 1X2, O/U, BTTS, xG).
5. **OpenAI** : brancher `openai_summary.py` avec les stats + probas pour générer le résumé et le scenario #1.
6. **Cron** : script `ingest_matches.py` + cron-job.org ou GitHub Actions pour rafraîchir les données régulièrement.

---

## 9. Schéma ASCII — flux /predict

```
  Client (Next.js)                FastAPI                        Supabase / ML
       │                             │                                  │
       │  POST /predict               │                                  │
       │  { home_team, away_team }   │                                  │
       │ ──────────────────────────► │                                  │
       │                             │  Auth JWT → user_id               │
       │                             │  subscription.check(user_id)     │
       │                             │ ────────────────────────────────►│
       │                             │  ◄── plan, analyses_used_today   │
       │                             │  Si free et >= 1 → 403           │
       │                             │  Charger features (teams, H2H)   │
       │                             │ ────────────────────────────────►│
       │                             │  ◄── feature vector              │
       │                             │  poisson.predict() → xG, scores  │
       │                             │  xgboost (optionnel) → 1X2, O/U   │
       │                             │  openai_summary() → résumé        │
       │                             │  Incrémenter analyses_used_today │
       │                             │  Log analysis_log                │
       │                             │ ────────────────────────────────►│
       │  ◄───────────────────────── │  JSON réponse                    │
       │  { xg, 1x2, over_under,     │                                  │
       │    btts, exact_score,        │                                  │
       │    summary, scenario_1 }    │                                  │
```

Tu peux utiliser ce document comme référence pour implémenter chaque brique dans l’ordre des étapes ci-dessus.
