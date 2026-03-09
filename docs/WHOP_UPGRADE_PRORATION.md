# Upgrade Starter → Pro/Lifetime avec proration (Whop)

## Ce que fait l’app

- Quand un utilisateur **Starter** clique sur **Pro** ou **Lifetime**, l’app envoie son **`whop_membership_id`** dans l’URL de checkout (`membership_id=...`).
- L’email est aussi prérempli pour que Whop reconnaisse le même client.

Cela permet à Whop d’appliquer un **upgrade au prorata** si leur côté le gère (même client, même company, passage à un plan supérieur).

## Côté Whop (Dashboard)

1. **Même company**  
   Starter, Pro et Lifetime doivent être des plans du **même produit / même company** Whop (déjà le cas si tes liens checkout pointent vers la même company).

2. **Proration / upgrade**  
   - Dans le **Dashboard Whop** → ton produit → paramètres des plans, vérifie s’il existe une option du type **“Allow plan upgrades”** ou **“Proration”** ou **“Switch plan”**.
   - Si tu ne la vois pas : contacter le **support Whop** pour demander comment activer la **proration à l’upgrade** (Starter → Pro ou Lifetime) pour un même client.

3. **Paramètre `membership_id`**  
   L’app envoie déjà `membership_id` en query string. Si Whop ne documente pas ce paramètre, ils peuvent l’ignorer sans casser le checkout. S’ils le supportent (ou l’ajoutent plus tard), la proration pourra s’appliquer automatiquement.

## Résumé

- **Code** : on envoie `membership_id` + `email` pour tout passage à un plan supérieur (Pro/Lifetime).
- **Whop** : activer la proration / l’upgrade dans le Dashboard ou avec le support, et garder tous les plans dans la même company.
