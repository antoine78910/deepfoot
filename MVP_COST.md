# Visifoot 2.0 — Budget MVP (~0–10 €/mois)

## Objectif

Garder les coûts entre **0 et 10 €/mois** pendant la phase MVP.

## Répartition des coûts

| Poste | Solution | Coût estimé |
|-------|----------|-------------|
| **Hébergement API** | Render free tier ou Fly.io free / Railway 5$/mois | 0–5 €/mois |
| **Frontend** | Vercel (free) | 0 € |
| **Base de données** | Supabase free (500 Mo, 2 projets) | 0 € |
| **Auth** | Supabase Auth (inclus) | 0 € |
| **Données matchs** | API gratuite (API-Football free tier) ou CSV open data | 0 € |
| **OpenAI** | 1 appel résumé + 1 scénario par analyse (gpt-4o-mini) | ~0,01 €/analyse |
| **Cron / jobs** | cron-job.org, GitHub Actions ou Cursor manuel | 0 € |

**Total typique** : 0 € (tout en free) ou 5–10 € si tu héberges l’API sur un petit plan payant.

## Optimisations pour rester low-cost

1. **Cache des prédictions**  
   Enregistrer en base le résultat par (home_team, away_team, date). Si même requête dans la journée, renvoyer le cache au lieu de recalculer + rappeler OpenAI.

2. **OpenAI uniquement si utile**  
   Résumé + scénario seulement pour les nouvelles analyses (pas pour les cache hits). Utiliser `gpt-4o-mini` pour limiter le coût par requête.

3. **Pas de serveur ML dédié**  
   Poisson + XGBoost tournent dans l’API (Python). Entraînement XGBoost (si tu l’actives) en job ponctuel (ex. hebdo) sur la même machine ou en local.

4. **Un seul projet Supabase**  
   Tout dans un projet (tables + Auth). RLS pour sécuriser par utilisateur.

5. **Limite free = 1 analyse/jour**  
   Réduit le volume d’appels API et OpenAI pour les utilisateurs non premium.

6. **Ingestion données**  
   Cron léger (ex. 1×/jour) pour mettre à jour résultats et H2H, pas de polling en temps réel.

## Évolution possible

- **Premium** : analyses illimitées, optionnellement datasets premium (xG, Opta) plus tard.
- **Scale** : si trafic augmente, monter l’API sur un plan payant (Railway, Render, etc.) et garder Supabase free tant que la limite ne bloque pas.
