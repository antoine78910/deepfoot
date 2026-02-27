# Roadmap — Améliorer la prédictivité du modèle

## 1. Poisson amélioré

### 1.1 Bivarié (corrélation buts domicile / extérieur)
- **Actuel** : `P(i,j) = Poisson(i|λ_h) × Poisson(j|λ_a)` (indépendance).
- **Amélioration** : Modèle bivarié (ex. copule, ou Poisson bivarié avec paramètre de corrélation) pour capturer la corrélation négative typique (si domicile marque beaucoup, extérieur marque un peu moins dans le même match).
- **Priorité** : Moyenne. Gain surtout sur les scores extrêmes et Over/Under.

### 1.2 Facteurs multiplicatifs
- **Absences joueurs clés** : Réduction de λ (ex. -10 % à -20 %) si absence de buteur / meneur. Nécessite une source de données (compos, blessures).
- **Fatigue** : Facteur sur λ selon densité du calendrier (matchs sur N jours). Données : nombre de matchs sur les 7–14 derniers jours.
- **Priorité** : Moyenne / basse tant qu’on n’a pas de données blessures/calendrier fiables.

---

## 2. Données enrichies

### 2.1 Expected goals (xG) réels
- **Actuel** : xG = λ issu des buts réels (moyennes buts marqués/encaissés).
- **Amélioration** : Intégrer des xG par équipe/match depuis une API (Understat, Opta, API-Football si disponible) et les utiliser comme base pour λ (ou mélange buts réels / xG).
- **Priorité** : Haute si source xG disponible.

### 2.2 Cotes bookmakers
- **Objectif** : Calibration et mesure de “value”. Comparer nos probabilités aux cotes (cote implicite = 1/odd) pour détecter les écarts.
- **Usage** : Pas forcément en entrée du modèle ; surtout pour validation (voir § 5) et affichage “value” côté produit.
- **Priorité** : Haute pour la validation ; moyenne pour l’intégration en entrée (régularisation).

### 2.3 Indicateurs avancés
- **Pressing, possession, tirs cadrés** : Amélioreraient la qualité des features (attaque/défense “réelles”). Dépend de la disponibilité des données (API-Football, autres).
- **Priorité** : Moyenne quand les données sont disponibles.

---

## 3. Historique et poids temporel

### 3.1 Forme récente pondérée
- **Actuel** : Derniers 5 matchs, même poids.
- **Amélioration** : Pondération exponentielle (ex. poids = exp(-decay * (k-1)) pour le k-ième match en arrière). Les matchs les plus récents pèsent plus.
- **Implémentation** : Dans `compute_goals_avg` et dans le calcul des “form points”, appliquer des poids par match.
- **Priorité** : Haute (simple et impactant).

### 3.2 H2H pondéré selon l’ancienneté
- **Actuel** : H2H = comptage brut (home_wins, draws, away_wins).
- **Amélioration** : Pondérer chaque match H2H par ancienneté (matchs récents plus pertinents). Idéal : 3 dernières saisons ; max 5 avec décroissance.
- **Outil** : Script `h2h_breakdown.py` (breakdown par saison + pondération) + intégration optionnelle dans `build_comparison_pcts` / calcul des lambdas.
- **Priorité** : Haute.

---

## 4. Machine Learning + Poisson

### 4.1 Garder Poisson comme baseline
- Le modèle actuel reste la référence : sorties 1X2, score exact, Over/Under, BTTS à partir de la grille Poisson.

### 4.2 Ajuster les lambdas par ML
- **Idée** : Entraîner un petit modèle (régression, XGBoost, etc.) qui prédit (λ_home, λ_away) ou un correctif (Δλ_home, Δλ_away) à partir de :
  - λ Poisson “naïf” (actuel),
  - features additionnelles (forme pondérée, H2H pondéré, xG si dispo),
  - éventuellement cotes bookmaker.
- **Objectif** : Réduire l’écart entre prévision Poisson et résultats réels sur l’historique (backtest).
- **Priorité** : Après mise en place du backtest et des métriques (§ 5).

---

## 5. Validation

### 5.1 Backtest sur 2–3 dernières saisons
- **Métriques** :
  - **1X2** : % de matchs où le résultat (1, N, 2) prédit (argmax des probas) est correct.
  - **Score exact top 5** : % de matchs où le score réel est dans les 5 scores les plus probables.
  - **Over/Under (ex. 2.5)** : % de matchs où (total buts > 2.5) est correct par rapport à la prévision (Over si P(Over) > 0.5).
- **Point-in-time** : Pour chaque match historique, utiliser uniquement les résultats **avant** la date du match pour calculer forme, H2H et lambdas.
- **Implémentation** : Module `backend/app/ml/validation.py` + API admin `POST /admin/backtest` + interface Admin (voir § 6).

### 5.2 Comparaison avec les bookmakers
- **Benchmark** : Cotes bookmaker → probabilités implicites (1/odd normalisées). Comparer :
  - notre taux de bon 1X2 vs “toujours parier le favori bookmaker” ;
  - log-loss ou Brier de nos probas vs résultats réels, et vs probas bookmaker.
- **Value** : Identifier les cas où notre modèle donne une proba nettement différente de la cote (écart > seuil) et mesurer le taux de succès sur ces paris “value”.
- **Priorité** : Haute une fois le backtest en place.

---

## 6. Partie Admin et backtest

### 6.1 Objectif
- Tester le modèle sur des saisons passées et des matchs réels.
- Afficher un **taux de réussite** (1X2, score exact top 5, Over/Under) pour améliorer le ML et la confiance dans le modèle.

### 6.2 Ce qui est mis en place
- **Backend**
  - `backend/app/ml/validation.py` : backtest point-in-time (chargement des résultats Supabase, calcul des lambdas par match, prédiction, agrégation des métriques).
  - `backend/app/api/admin.py` : route `POST /admin/backtest` (paramètres : ligue, plage de dates ou saisons). Protégée par clé API admin ou rôle.
- **Frontend**
  - Page **Admin** (ex. `/app/admin`) : formulaire (ligue optionnelle, saison début / fin), bouton “Lancer le backtest”, affichage des résultats (taux 1X2, exact top 5, O/U 2.5, nombre de matchs).
- **Script H2H**
  - `backend/scripts/h2h_breakdown.py` : recherche tous les matchs type “Lorient – Auxerre” (via API-Football ou noms), breakdown par saison, idéal 3 dernières saisons, max 5 avec pondération (poids décroissant par ancienneté).

### 6.3 Préconisation
1. **Remplir Supabase** avec au moins 2–3 saisons de résultats. Le script `ingest_matches.py` actuel ne récupère que la saison courante ; pour un backtest pertinent, étendre le script pour ingérer plusieurs saisons (ex. 2022, 2023, 2024) ou importer un export historique si disponible.
2. **Lancer régulièrement le backtest** depuis l’admin pour suivre l’évolution des métriques après chaque changement (pondération temporelle, H2H pondéré, etc.).
3. **Enchaîner** avec l’ajustement des lambdas par ML une fois les métriques stables et documentées.
