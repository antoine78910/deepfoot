# Modèle d'analyse de match — Documentation complète

Ce document décrit **tout** ce qui se passe lors d’une analyse de match : requêtes API, calculs des probabilités, données utilisées, et génération du résumé IA. Il sert de base pour optimiser le modèle.

---

## 1. Vue d’ensemble du flux (temps de chargement)

Quand l’utilisateur lance une analyse (frontend → `POST /predict/stream`) :

| Étape | % progress | Ce qui se fait |
|--------|------------|----------------|
| **Initializing…** | 0% | Début de `run_predict_with_progress` |
| **load_match_context** | 0→62% | Toutes les requêtes données + feature engineering (voir §2) |
| **Computing probabilities…** | 62% | Modèle Poisson à partir de `lambda_home`, `lambda_away` (voir §3) |
| **Generating AI summary…** | 75% | Contexte texte + news (optionnel) + 1 appel OpenAI (voir §4) |
| **Done** | 100% | Assemblage de la réponse (`_build_response`) |

Ensuite le frontend reçoit le résultat en stream (NDJSON) et l’affiche.

---

## 2. Chargement des données (`load_match_context`)

**Fichier :** `backend/app/services/data_loader.py`

### 2.1 Source prioritaire : API-Football (api-sports.io)

Si `API_FOOTBALL_KEY` est configuré, tout le contexte vient d’API-Football v3 (`https://v3.football.api-sports.io`).

#### 2.1.1 Résolution des équipes (5%)

- Si **home_team_id** et **away_team_id** sont fournis (autocomplete) → pas de résolution, on les utilise.
- Sinon : **resolve_team_name_to_id(name)** pour chaque équipe.
  - Utilise un **cache global** des équipes : au premier appel, `_fill_teams_cache()` charge les équipes de **toutes les ligues** configurées (`LEAGUE_IDS` dans `app/core/leagues.py`).
  - **Nombre de requêtes pour remplir le cache :** 1 × **nombre de ligues** (GET `/teams?league={id}&season={year}`). Il y a ~45 ligues → **jusqu’à 45 requêtes** au premier usage de l’API sur l’instance.
  - La résolution elle-même ne fait **aucune requête** supplémentaire (lookup dans le cache).

#### 2.1.2 Infos équipes + prochain match (15%)

- **get_team_by_id(home_id)** et **get_team_by_id(away_id)** : 2 requêtes GET `/teams?id={id}` (logos, noms, stade).
- **get_team_upcoming_fixtures(home_id, next_n=15)** : 1 requête GET `/fixtures?team={id}&next=15` pour trouver le **prochain match commun** Home vs Away (fixture_id, date, ligue, lieu).

#### 2.1.3 Forme des équipes (28%)

- **get_team_fixtures(home_id, season, last_n=10)** et **get_team_fixtures(away_id, season, last_n=10)** : 2 requêtes GET `/fixtures?team={id}&season={year}&status=FT` (en parallèle via `ThreadPoolExecutor`).
- On en déduit pour chaque équipe (sur les **5 derniers matchs**) :
  - **goals_for** / **goals_against** (listes de 5 entiers),
  - **form** (liste de 5 résultats : W/D/L).

Données utilisées : **5 matchs × 2 équipes = 10 matchs** pour la forme.

#### 2.1.4 Head-to-head (52%)

- **get_fixtures_headtohead_multi_season(home_id, away_id, ideal_seasons=5, max_seasons=5)** :
  - Pour chaque saison (5 saisons : N, N-1, …, N-4) et pour chaque équipe (home, away), 1 requête GET `/fixtures?team={id}&season={year}&status=FT`.
  - Donc **5 × 2 = 10 requêtes**.
  - On filtre côté code pour ne garder que les matchs entre les deux équipes (fusion, dédoublonnage par fixture id).
- **get_h2h_from_fixtures** : calcul (home_wins, draws, away_wins) à partir de la liste de fixtures (pas de requête).
- **get_weighted_h2h_home_pct** : pourcentage H2H pondéré (saison récente = 1.0, puis 0.8, 0.6, 0.4, 0.2). Pas de requête.

Nombre de **matchs H2H** utilisés : tous ceux trouvés sur les 5 dernières saisons (variable, souvent 0 à ~20+).

#### 2.1.5 Ligue / date / lieu (fallback)

- Si ligue ou date ou lieu manquent et qu’on a des H2H : on les prend depuis le **dernier match H2H** (déjà en mémoire).
- **guess_common_league_name(home_id, away_id)** (si ligue toujours manquante) :
  - **get_team_leagues(home_id)** et **get_team_leagues(away_id)** : 2 requêtes GET `/leagues?team={id}&season={year}`.
  - On déduit une ligue commune (type "league") partagée par les deux.

#### 2.1.6 Match terminé (dernier H2H) et statistiques

- Si **aucun prochain match** trouvé mais qu’on a des H2H :
  - **get_fixture_by_id(last_fid)** : 1 requête GET `/fixtures?id={id}` pour savoir si le dernier H2H est terminé (FT) et récupérer le score.
  - Si status = FT : **get_fixture_statistics(fixture_id, home_id, away_id)** : 1 requête GET `/fixtures/statistics?fixture={id}` pour les stats du match (possession, tirs, etc.).

#### 2.1.7 Feature engineering (58%)

- **compute_goals_avg** : moyennes des buts marqués et encaissés (sur les 5 derniers matchs).
- **compute_lambda_home_away** : calcul des **λ_home** et **λ_away** pour le modèle de Poisson (voir §3.1).
- **build_comparison_pcts** : calcul des pourcentages pour les barres (attack, defense, form, h2h, goals, overall). Utilise notamment **h2h_home_pct_override** = H2H pondéré si disponible.

### 2.2 Récapitulatif des requêtes API-Football par analyse

| Phase | Requêtes | Détail |
|--------|----------|--------|
| Résolution noms → IDs | 0 ou ~45 | 0 si IDs fournis ; sinon 1× par ligue au 1er appel (cache) |
| Team info + upcoming | 3 | 2× GET /teams?id=, 1× GET /fixtures?team=&next=15 |
| Forme | 2 | 2× GET /fixtures?team=&season=&status=FT (last 10) |
| H2H multi-saison | 10 | 5 saisons × 2 équipes × GET /fixtures |
| Ligue commune (si besoin) | 2 | 2× GET /leagues?team=&season= |
| Dernier H2H + stats (si pas de prochain match) | 0 à 2 | GET /fixtures?id=, GET /fixtures/statistics?fixture= |

**Total typique par analyse (IDs déjà fournis, cache déjà rempli) :** 3 + 2 + 10 + (0 à 2) + (0 ou 2) ≈ **17 à 21 requêtes**.

**Premier appel (sans cache) :** + ~45 requêtes pour remplir le cache des équipes.

### 2.3 Source de secours : Supabase

Si pas de clé API-Football (ou résolution / données insuffisantes), on utilise Supabase :

- **get_team_results(team_slug, is_home, last_n=5)** : table `results` (home_team_id, away_team_id, home_goals, away_goals), 1 requête par équipe.
- **get_team_form(team_slug, last_n=5)** : table `results`, 1 ou 2 requêtes.
- **get_h2h(home_slug, away_slug)** : table `h2h` (home_wins, draws, away_wins), 1 requête.

Puis **compute_goals_avg**, **compute_lambda_home_away**, **build_comparison_pcts** comme ci-dessus.

### 2.4 Données produites par `load_match_context`

- **home_team**, **away_team** (noms normalisés)
- **home_team_id**, **away_team_id**
- **lambda_home**, **lambda_away** (intensités Poisson)
- **home_form**, **away_form** (listes W/D/L, 5 éléments)
- **home_wdl**, **away_wdl** (ex. "3-1-1")
- **home_form_label**, **away_form_label** ("Great form" / "Average form" / "Poor form")
- **comparison_pcts** : attack_home_pct, defense_home_pct, form_home_pct, h2h_home_pct, goals_home_pct, overall_home_pct
- **league**, **match_date**, **match_date_iso**, **venue**
- **fixture_id** (si prochain match trouvé)
- **home_team_logo**, **away_team_logo**
- **match_over**, **final_score_home**, **final_score_away**, **match_statistics** (si dernier H2H terminé)

---

## 3. Calcul des probabilités (modèle Poisson)

**Fichier :** `backend/app/ml/poisson.py`  
**Fichier features :** `backend/app/ml/features.py`

### 3.1 Calcul des lambdas (xG)

- **compute_lambda_home_away** (features.py) :
  - **h_for** = moyenne(goals_for home), **h_against** = moyenne(goals_against home).
  - **a_for** = moyenne(goals_for away), **a_against** = moyenne(goals_against away).
  - **league_avg_goals** = 2.7 (défaut).
  - Formule (style Dixon–Robinson) :
    - `lambda_home = (h_for * a_against) / (league_avg_goals / 2)`
    - `lambda_away = (a_for * h_against) / (league_avg_goals / 2)`
  - **Lissage :** lambda_home et lambda_away sont clampés entre **0.2** et **4.0**.

Les **xG** affichés sont exactement **lambda_home** et **lambda_away** (arrondis à 2 décimales). Aucune autre donnée (H2H, forme brute) n’entre dans le calcul des lambdas : uniquement les moyennes de buts marqués/encaissés sur les 5 derniers matchs.

### 3.2 Grille de score et dérivés

- **poisson_score_grid(λ_home, λ_away)** : pour chaque (i, j) avec i, j ∈ {0, 1, …, max_goals} (max_goals = 8 par défaut) :
  - **P(i–j) = Poisson(i | λ_home) × Poisson(j | λ_away)**.
- **prob_1x2_from_grid** :
  - P(1) = somme des P(i,j) pour i > j  
  - P(Nul) = somme pour i = j  
  - P(2) = somme pour i < j  
- **prob_over_under(line, grid)** : pour chaque ligne 0.5, 1.5, 2.5, 3.5, P(Over) = somme des P(i,j) pour i+j > line.
- **prob_btts(grid)** : P(BTTS Yes) = somme des P(i,j) pour i ≥ 1 et j ≥ 1.
- **exact_score_probs** : tous les (i, j, P(i,j)), triés par proba décroissante ; on garde le **top 5**.
- **prob_total_goals_distribution** : P(total = 0, 1, 2, 3+).
- **prob_goal_difference_distribution** : P(écart = 1, 2, 3+).
- **prob_asian_handicap** : Home -1, Home +1, Away -1, Away +1 (définis comme dans le code).

Aucun poids différent par type d’événement : tout est dérivé de la **même** grille Poisson. Les “events” qui “comptent plus” n’existent pas en tant que tels ; ce qui varie, c’est la **construction des λ** (uniquement buts pour/contre sur 5 matchs) et l’usage qu’on en fait (1X2, O/U, BTTS, etc.).

### 3.3 Sortie de `predict_all`

- xG (lambda_home, lambda_away, total)
- 1X2 (prob_home, prob_draw, prob_away) et cotes implicites
- BTTS (btts_yes_pct, btts_no_pct)
- Over/Under pour 0.5, 1.5, 2.5, 3.5
- Exact scores (top 5) et most_likely_score
- total_goals_distribution, goal_difference_dist
- double_chance_1x, x2, 12
- asian_handicap
- upset_probability = min(P(1), P(2))×100

### 3.4 Mode “API-Football Predictions” (optionnel)

Si **use_api_predictions=True** et qu’un **fixture_id** existe :

- 1 requête **GET /predictions?fixture={id}** (API-Football).
- Les probas 1X2, xG (moyennes last_5 de l’API), Over/Under (une ligne) viennent de cette API. BTTS, exact_scores, grilles complètes sont mis en valeurs neutres (50/50 ou vides) pour garder le schéma de réponse.

---

## 4. Barres de comparaison (attack, defense, form, H2H, goals, overall)

**Fichier :** `backend/app/ml/features.py` → **build_comparison_pcts**

- **attack_home_pct** : 100 × home_goals_for / (home_goals_for + away_goals_for). Données : moyennes de buts marqués (sur 5 matchs).
- **defense_home_pct** : basé sur 1/(goals_against). Plus une équipe encaisse peu, plus sa “défense” est forte. Proportion normalisée entre home et away.
- **form_home_pct** : points (3W+1D+0L) sur 3×n, normalisés entre les deux équipes (somme = 100%).
- **h2h_home_pct** : si **h2h_home_pct_override** (H2H pondéré 5 saisons) est fourni, on l’utilise ; sinon (home_wins + 0.5×draws) / total_h2h × 100. Les matchs récents pèsent plus (poids 1.0, 0.8, 0.6, 0.4, 0.2 par saison).
- **goals_home_pct** : même logique qu’attack (part des buts “for”).
- **overall_home_pct** : **moyenne des 5** (attack, defense, form, h2h, goals). Toutes les dimensions ont le **même poids** (1/5 chacune).

Donc : **aucun event ne compte plus qu’un autre** dans l’overall ; on peut envisager des poids différents (ex. H2H ou form plus forts) pour optimiser.

---

## 5. Génération du résumé IA (“Generating AI summary…”)

**Fichiers :** `backend/app/services/openai_summary.py`, `backend/app/services/news_fetcher.py`

### 5.1 Contexte envoyé au LLM

- **build_prompt_context** construit une chaîne avec :
  - Match: {home} vs {away}
  - Expected goals: {home} {xg_home}, {away} {xg_away}
  - Probabilities 1X2: Home {prob_home}%, Draw {prob_draw}%, Away {prob_away}%
  - Form: {home} form: {home_form_label}. {away} form: {away_form_label}.
  - League: {league}. Venue: {venue}.

- Ensuite, si **NEWS_API_KEY** est configuré : **fetch_football_news(home_team, away_team, league)** :
  - Pour chaque équipe (et optionnellement la ligue), 1 requête GET à **NewsAPI.org** (`/v2/everything?q="Team" football&language=...&pageSize=3&from=...`).
  - Max 7 jours, max 3 articles par équipe, jusqu’à 8 snippets au total.
  - Le texte est ajouté au contexte sous la forme : `"Latest football news (use if relevant for the summary):\n" + snippets`.

Donc le **contexte résumé** = **texte structuré (match, xG, 1X2, forme, ligue, lieu)** + **optionnellement actualités**.

### 5.2 Un seul appel OpenAI

- **generate_ai_analysis(prompt_ctx, home_team, away_team, language)** :
  - 1 appel **chat.completions.create** (modèle **gpt-4o-mini**, max_tokens=1200, response_format=json_object).
  - La langue est forcée en **fr**, **en** ou **es** selon `language`, sinon “same language as team names”.
  - Le prompt système demande un JSON avec : **quick_summary**, **scenario_1**, **scenario_2**, **scenario_3**, **scenario_4**, **key_forces_home**, **key_forces_away**.
  - **scenario_2/3/4** : objets { title, body, probability_pct }.
  - Instructions pour utiliser les vrais noms d’équipes/ligue/lieu et, si des news sont fournies, les mentionner dans le résumé.

**Résumé :** on ne “summarize” pas des documents externes ; on **envoie un bloc de contexte (stats + optionnel news)** et le LLM génère en une fois tout le texte (résumé + scénarios + points forts). Aucun résumé intermédiaire de type “résumer 10 articles puis résumer le résumé”.

---

## 6. Assemblage de la réponse

**_build_response** (predict.py) fusionne :

- Contexte (équipes, ligue, date, lieu, logos, form, comparison_pcts, match_over, score, stats).
- Sortie du modèle (Poisson ou API Predictions) : xG, 1X2, BTTS, O/U, exact scores, etc.
- Sortie IA : quick_summary, scenario_1, scenario_2, scenario_3, scenario_4, key_forces_home, key_forces_away.

---

## 7. Pistes d’optimisation

- **Requêtes API-Football :** réduire le nombre de ligues dans le cache, ou lazy-load par ligue ; mutualiser les appels H2H si possible ; éviter `guess_common_league_name` quand la ligue est déjà connue.
- **Données entrantes :** augmenter ou diminuer le nombre de matchs (aujourd’hui 5 pour la forme, 10 fixtures récupérées) ; inclure ou non les compétitions (coupe vs championnat) dans la forme.
- **Lambdas :** tester d’autres formules (ex. pondération par date des matchs, ou prise en compte H2H dans λ) ; ajuster **league_avg_goals** ou le lissage [0.2, 4.0].
- **Barres :** pondérer différemment attack / defense / form / H2H / goals dans **overall_home_pct** (ex. H2H ou form plus fort).
- **IA :** un seul appel est déjà économique ; on peut réduire max_tokens ou restreindre les champs si besoin coût/latence.
- **News :** désactiver ou limiter (1 requête par équipe au lieu de 2) si peu de valeur ajoutée.

---

## 8. Résumé des nombres

| Élément | Valeur |
|--------|--------|
| Matchs utilisés pour la forme | 5 derniers par équipe (10 au total) |
| Matchs H2H utilisés | Tous trouvés sur 5 saisons (variable) |
| Saisons H2H | 5 (poids 1.0, 0.8, 0.6, 0.4, 0.2) |
| Grille Poisson | (max_goals+1)² = 81 cases (0..8 buts) |
| Requêtes API-Football (analyse typique) | 17 à 21 (sans cache) ; + ~45 au 1er remplissage cache |
| Requêtes NewsAPI (si configuré) | 1 ou 2 (par équipe) |
| Appels OpenAI par analyse | 1 (gpt-4o-mini, ~1200 tokens max) |
| Dimensions “overall” (barres) | 5 (attack, defense, form, h2h, goals), poids égaux 1/5 |

Ce document reflète l’état du code au moment de sa rédaction (backend/app : data_loader, api_football, ml/poisson, ml/features, openai_summary, news_fetcher, api/predict).
