# Upgrade Starter → Pro/Lifetime avec proration (Whop)

## Flux upgrade (avec prorata)

Quand un client **déjà abonné** (Starter ou Pro) veut passer à un plan supérieur :

1. L’app redirige vers la **page de gestion d’abonnement Whop** (`manage_url` de sa membership), pas vers un lien checkout plan.
2. Sur cette page, le client voit les autres plans du produit, choisit le plan supérieur.
3. **Whop calcule le prorata** : le client ne paie que la différence pour le reste du cycle, puis le nouveau tarif au prochain renouvellement.

## Ce que fait l’app

- **Backend** : l’endpoint `/me` appelle l’API Whop `GET /memberships/{id}` et renvoie **`whop_manage_url`** (champ `manage_url` de la membership).
- **Frontend** : pour tout clic « Upgrade » (Starter→Pro, Starter→Lifetime, Pro→Lifetime), si l’utilisateur a `whop_manage_url`, on redirige vers cette URL. Sinon (fallback) on utilise le lien checkout classique avec `membership_id`.
- **Nouvel abonnement** (utilisateur free) : lien checkout normal vers le plan choisi (pas de manage_url).

## Résumé

- **Upgrade** → `whop_manage_url` (page gestion Whop, prorata géré par Whop).
- **Nouveau** → lien checkout plan + email (optionnellement `prefilled_identification[email]`).
