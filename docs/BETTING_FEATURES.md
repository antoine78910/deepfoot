# Features paris — ajoutées vs non ajoutées

## ✅ Features ajoutées (fiables, dérivées du modèle Poisson)

Toutes celles-ci sont calculées à partir de la même grille de probabilités de score (Poisson) que le 1X2 et le BTTS. Aucune donnée externe supplémentaire.

| Feature | Description | Fiable car |
|--------|-------------|------------|
| **Cotes implicites 1X2** | Cote décimale = 100 / probabilité (pour comparer aux bookmakers) | Formule directe à partir de nos probs. |
| **Score le plus probable** | Ex. 2-1 avec 18 % | Premier des scores exacts déjà calculés. |
| **Score attendu moyen (xG)** | Ex. 1,8 – 1,2 | Déjà en sortie (xg_home, xg_away). |
| **Distribution total buts** | P(0, 1, 2, 3+ buts dans le match) | Somme sur la grille P(i+j=k). |
| **Buts par équipe** | xG domicile / extérieur | Déjà en sortie. |
| **Double chance** | 1X, X2, 12 (probabilités) | 1X = P(1)+P(X), etc. |
| **Handicap asiatique** | Home -1, Home +1, Away -1, Away +1 (prob. de couvrir) | Probabilités dérivées de la grille (ex. Home +1 = P(home ≥ away)). |
| **BTTS** | Oui/Non + probabilité | Déjà en sortie. |
| **Écart de buts** | P(écart = 1, 2, 3+ buts) | Somme sur la grille pour \|i-j\|. |
| **Probabilité d’upset** | Probabilité que l’outsider gagne | min(P(1), P(2)). |

---

## ❌ Features non ajoutées (pas fiables avec le modèle actuel)

| Feature demandée | Raison de ne pas l’ajouter |
|------------------|----------------------------|
| **Minute probable du premier but / intervalle** | Le modèle ne travaille que sur le score final (nombre de buts par équipe). Il n’y a **aucune information temporelle** (minute, période). Estimer une minute ou un intervalle serait un chiffre sorti de nulle part, pas une sortie du modèle. Pour être fiable, il faudrait des données « premier but à la minute X » ou un modèle dédié. |
| **Tendance live** (ex. « Si score 1-0 à la 70e, x % de chance de gagner ») | C’est du **live betting** : probabilités conditionnelles au score actuel et au moment du match. Notre modèle est **pré-match** (avant le coup d’envoi). Pour faire du conditionnel « si 1-0 à 70’ », il faudrait un modèle d’in-game (états du match, temps restant, etc.) et éventuellement des données live. Non implémenté. |
| **Fatigue des joueurs / absences / blessures** | Ces indicateurs demandent des **données externes** : compositions, minutes jouées, blessures, suspensions. Nous n’avons pas ces données dans le pipeline actuel (API-Football pour résultats et H2H, pas de line-ups ou d’infos blessures intégrées). Les afficher sans données serait trompeur. |
| **Momentum récent** | Déjà reflété par la **forme récente** (derniers matchs W/D/L) et les barres de comparaison (form, attack, etc.). Pas de feature supplémentaire ajoutée ici. |

---

## Résumé

- **Tout ce qui est dérivable uniquement de la grille Poisson** (1X2, scores exacts, Over/Under, BTTS, double chance, handicap asiatique, distribution buts, écart, upset, cotes implicites) est **ajouté et cohérent** avec le modèle.
- **Tout ce qui dépend du temps dans le match** (minute du premier but, tendance live) ou **de données que nous n’avons pas** (fatigue, absences) n’est **pas ajouté** pour rester fiable et honnête sur les limites du modèle.
