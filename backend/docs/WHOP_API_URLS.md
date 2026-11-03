# URLs Whop API appelées par le backend

Toutes ces routes sont **compatibles Company API Key** (pas de route `/me` ni de routes user-scoped OAuth).

## Pourquoi on avait "does not have permission to access this route"

- **Company API keys** ne doivent appeler que l’API **v1** : `https://api.whop.com/api/v1/...`
- Les routes **v5** et **v2** sous `/company/*` (ex. `/api/v5/company/members`, `/api/v2/company/memberships`) sont prévues pour les **App API keys** (apps installées sur plusieurs companies). Avec une Company API key, Whop renvoie **401 "The API Key supplied does not have permission to access this route"**.
- Les routes **/me** de Whop (ex. `/api/v2/me/memberships`) nécessitent un **token OAuth utilisateur**, pas une Company API key.

**Règle à ne pas changer :** avec une Company API key, n’appeler que des endpoints **v1** documentés pour Company (members, memberships, payments, cancel). Ne pas réintroduire d’appels à v5/v2 `/company/*` ni à `/me`.

## me.py (plan, sync, annulation)

| Méthode | URL exacte |
|--------|------------|
| GET | `https://api.whop.com/api/v1/members?company_id={company_id}&first=100` |
| GET | `https://api.whop.com/api/v1/memberships?company_id={company_id}&statuses=active&user_ids={user_id}&first=50` |
| POST | `https://api.whop.com/api/v1/memberships/{membership_id}/cancel` |
| GET | `https://api.whop.com/api/v1/payments?membership_id={id}&first=20` |
| POST | `https://api.whop.com/api/v1/payments/{payment_id}/refund` (`partial_amount` = prorata unused month) |

Aucune route v2 ni v5 `/company/*` n’est appelée (elles nécessitent une App API Key et renvoient 401 avec une Company API Key).

## webhooks.py (récupération payment)

| Méthode | URL exacte |
|--------|------------|
| GET | `https://api.whop.com/api/v1/payments/{payment_id}` |
| GET | `https://api.whop.com/api/v5/company/payments/{payment_id}` (fallback) |

La v1 est essayée en premier pour les Company API Keys.
