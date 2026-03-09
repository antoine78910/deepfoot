# Configuration du webhook Whop (paiements + sync plan)

## Pourquoi je n’ai pas de notification quand quelqu’un paye ?

Le backend ne reçoit les événements Whop (paiement réussi, etc.) **que si un webhook est configuré** dans le dashboard Whop et pointe vers votre API.

1. **Créer le webhook dans Whop**
   - Aller sur [Whop Dashboard](https://whop.com/dashboard) → **Developer** (ou **Settings** → **Developer** / **Webhooks**).
   - Créer un webhook :
     - **URL** : `https://<VOTRE_DOMAINE_API>/webhooks/whop`  
       Exemple : `https://votre-api.railway.app/webhooks/whop`
     - **Événements** : cocher au minimum **`payment.succeeded`** (et éventuellement `membership.went_invalid`, etc. pour révoquer l’accès).
   - Copier le **secret** du webhook (préfixe `ws_...`).

2. **Configurer le secret côté backend**
   - Dans les variables d’environnement de l’API (Railway, etc.), définir :
     - `WHOP_WEBHOOK_SECRET=ws_xxxx` (la valeur fournie par Whop).
   - Sans ce secret, les requêtes sont quand même acceptées mais la signature n’est pas vérifiée.

3. **Vérifier que les requêtes arrivent**
   - Consulter les logs de l’API (ex. Railway). Au moment d’un paiement test, vous devriez voir une ligne du type :
     - `Whop webhook received event=payment.succeeded` puis soit une mise à jour du plan, soit un message expliquant pourquoi rien n’a été mis à jour (email inconnu, etc.).

Si après ça vous ne voyez toujours aucune ligne de log au moment du paiement, le problème vient de Whop (URL incorrecte, événement non coché, ou webhook désactivé).

---

## Pourquoi le nouvel utilisateur n’apparaît pas sur mon dashboard ?

Le **dashboard de l’app** (liste des utilisateurs, analytics) affiche les **utilisateurs Supabase** : ce sont les personnes qui se sont **inscrites sur votre app** (sign up avec email / OAuth).

- **Payer sur Whop** ne crée **pas** d’utilisateur dans Supabase.
- Le webhook Whop fait uniquement : **mettre à jour le plan** d’un utilisateur **déjà existant** en cherchant son compte par **email**.

Donc :

- Si le client paie sur Whop avec l’email `client@example.com` mais **ne s’est jamais inscrit** sur l’app avec ce même email → il n’existe pas dans Supabase → le webhook ne peut pas le lier → **aucun “nouvel utilisateur”** sur votre dashboard et **aucune mise à jour de plan**.
- Pour que le plan soit bien mis à jour et que l’utilisateur “existe” chez vous :
  1. Le client doit **s’inscrire sur l’app** (avec l’email qu’il utilisera aussi sur Whop), **ou**
  2. Au minimum avoir un compte Supabase (Auth) avec **exactement le même email** que celui utilisé pour payer sur Whop.

En résumé : **même email** pour l’inscription app (Supabase) et pour le paiement Whop. Si tu as utilisé un “email temporaire” uniquement dans Whop et jamais pour te connecter à l’app, ce compte n’existe pas côté app, donc pas de nouvel user et pas de mise à jour de plan.

---

## Récap

| Problème | Cause probable | Action |
|----------|----------------|--------|
| Aucune “notification” / rien dans les logs au moment du paiement | Webhook Whop non configuré ou mauvaise URL | Configurer l’URL `https://<api>/webhooks/whop` et l’événement `payment.succeeded` dans Whop, puis vérifier les logs API. |
| Pas de nouvel utilisateur sur le dashboard après un paiement | Le client n’a pas de compte app (Supabase) avec cet email | Le client doit s’inscrire sur l’app avec **le même email** que sur Whop. |
| Paiement reçu par Whop mais plan pas mis à jour | Email Whop ≠ email du compte app | Utiliser le même email des deux côtés, ou vérifier dans les logs le message “no Supabase user found for email …”. |
