# Sitemap XML et architecture canonical (DeepFoot)

## URLs des sitemaps à soumettre

À soumettre dans **Google Search Console** et **Bing Webmaster Tools** :

| Sitemap        | URL                          | Usage                                      |
|----------------|------------------------------|--------------------------------------------|
| **Sitemap principal** | `https://deepfoot.ai/sitemap.xml`   | Toutes les pages (statiques + articles)     |
| **AI sitemap** | `https://deepfoot.ai/ai-sitemap.xml` | Pages clés pour crawlers / découverte      |

Tu n’as pas besoin de générer un fichier XML à la main : Next.js les génère à la volée. Il suffit de déployer et d’indiquer ces deux URLs dans les outils de soumission.

---

## Architecture canonical

**Règle unique :** l’URL canonique d’une page est toujours :

```
{SITE_URL}{path}
```

Avec `SITE_URL = https://deepfoot.ai` (défini dans `frontend/lib/seo/site.ts`).

- Pas de paramètres de requête dans le canonical.
- Pas de trailing slash (sauf si tu décides une convention et l’appliques partout).
- Une seule version du site en production (éviter deepfoot.ai vs www.deepfoot.ai sans redirection).

### Exemples

| Type de page   | path                    | Canonical                          |
|----------------|-------------------------|------------------------------------|
| Homepage       | `/`                     | `https://deepfoot.ai/`              |
| Article        | `/blog/mon-article`     | `https://deepfoot.ai/blog/mon-article` |
| Comparaison    | `/compare/deepfoot-vs-visifoot` | `https://deepfoot.ai/compare/deepfoot-vs-visifoot` |

---

## Écrire des articles (blog)

### 1. Structure des URLs

- **Segment fixe :** `/blog/`
- **Slug :** minuscules, tirets, pas d’accents ni caractères spéciaux.
- **Exemple :** `https://deepfoot.ai/blog/premier-league-predictions-2025`

### 2. Fichiers à créer

- **Route :** `frontend/app/blog/[slug]/page.tsx`
- **Metadata :** utiliser `buildArticleMetadata()` depuis `@/lib/seo/metadata`.
- **Schema :** utiliser `articleSchema()` depuis `@/lib/seo/schema` (JSON-LD Article).

### 3. Exemple de page article

```tsx
// app/blog/[slug]/page.tsx
import { buildArticleMetadata } from "@/lib/seo/metadata";
import { articleSchema } from "@/lib/seo/schema";
import { SITE_URL } from "@/lib/seo/site";

type Props = { params: { slug: string } };

export async function generateMetadata({ params }: Props) {
  const slug = params.slug;
  const path = `/blog/${slug}`;
  // Récupérer title, description, publishedTime depuis ton CMS ou MD
  const title = "Mon titre d'article";
  const description = "Meta description 150–160 caractères.";
  const publishedTime = "2025-03-10T12:00:00Z";

  return buildArticleMetadata({
    title,
    description,
    path,
    publishedTime,
  });
}

export default function BlogPostPage({ params }: Props) {
  const slug = params.slug;
  const path = `/blog/${slug}`;
  const canonical = `${SITE_URL}${path}`;
  const jsonLd = articleSchema({
    headline: "Mon titre",
    description: "…",
    url: canonical,
    datePublished: "2025-03-10T12:00:00Z",
    authorName: "DeepFoot",
  });

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd }} />
      <article>
        <h1>Mon titre</h1>
        {/* contenu */}
      </article>
    </>
  );
}
```

### 4. Ajouter un article au sitemap XML

Dans `frontend/lib/seo/sitemap-pages.ts`, la fonction `blogSitemapEntries()` retourne les URLs des articles. Pour l’instant elle retourne un tableau vide.

Quand tu ajoutes un article, tu dois l’ajouter à la liste (ou la générer depuis un CMS) :

```ts
// Dans blogSitemapEntries(), remplacer par quelque chose comme :
export function blogSitemapEntries(): MetadataRoute.Sitemap {
  const entries: BlogSitemapEntry[] = [
    {
      slug: "premier-league-predictions-2025",
      lastModified: new Date("2025-03-10"),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    // Autres articles…
  ];

  return entries.map((e) => ({
    url: `${SITE_URL}/blog/${e.slug}`,
    lastModified: e.lastModified,
    changeFrequency: e.changeFrequency ?? "monthly",
    priority: e.priority ?? 0.7,
  }));
}
```

Après déploiement, `https://deepfoot.ai/sitemap.xml` contiendra automatiquement `https://deepfoot.ai/blog/premier-league-predictions-2025`, etc.

### 5. Checklist pour chaque nouvel article

- [ ] URL en `/blog/[slug]`, slug lisible et stable.
- [ ] `generateMetadata` avec `buildArticleMetadata` et **path = `/blog/{slug}`**.
- [ ] Canonical = `https://deepfoot.ai/blog/{slug}` (géré par `buildArticleMetadata`).
- [ ] JSON-LD Article avec `articleSchema` (headline, description, url, datePublished, auteur si besoin).
- [ ] Entrée ajoutée dans `blogSitemapEntries()` (ou générée depuis la source des articles).

---

## Où tout est défini

| Élément            | Fichier / lieu |
|--------------------|----------------|
| URL canonique de base | `frontend/lib/seo/site.ts` → `SITE_URL` |
| Pages statiques du sitemap | `frontend/lib/seo/sitemap-pages.ts` → `staticSitemapEntries()` |
| Pages blog du sitemap | `frontend/lib/seo/sitemap-pages.ts` → `blogSitemapEntries()` |
| Génération sitemap.xml | `frontend/app/sitemap.ts` (concatène statique + blog) |
| Génération ai-sitemap.xml | `frontend/app/ai-sitemap.ts` |
| Metadata pages | `frontend/lib/seo/metadata.ts` → `buildPageMetadata` |
| Metadata articles | `frontend/lib/seo/metadata.ts` → `buildArticleMetadata` |
| Schema Article | `frontend/lib/seo/schema.ts` → `articleSchema` |

---

## Résumé

1. **Sitemap à “mettre” :** utilise directement `https://deepfoot.ai/sitemap.xml` et `https://deepfoot.ai/ai-sitemap.xml` dans les outils (rien à héberger à part).
2. **Canonical :** toujours `https://deepfoot.ai` + `path` ; pour les articles, `path = /blog/[slug]`.
3. **Nouveaux articles :** créer la page sous `app/blog/[slug]/page.tsx`, utiliser `buildArticleMetadata` + `articleSchema`, et ajouter l’entrée dans `blogSitemapEntries()`.
