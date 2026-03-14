import type { MetadataRoute } from "next";
import { SITE_URL } from "./site";

/**
 * Static pages included in sitemap.xml.
 * Add new marketing/SEO pages here.
 */
export function staticSitemapEntries(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE_URL, lastModified: now, changeFrequency: "daily" as const, priority: 1 },
    { url: `${SITE_URL}/ai-football-predictions`, lastModified: now, changeFrequency: "weekly" as const, priority: 0.95 },
    { url: `${SITE_URL}/how-ai-football-predictions-work`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.9 },
    { url: `${SITE_URL}/compare/deepfoot-vs-visifoot`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.9 },
    { url: `${SITE_URL}/alternatives/visifoot-alternative`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.9 },
    { url: `${SITE_URL}/analyse`, lastModified: now, changeFrequency: "daily" as const, priority: 0.9 },
    { url: `${SITE_URL}/app`, lastModified: now, changeFrequency: "weekly" as const, priority: 0.8 },
    { url: `${SITE_URL}/matches`, lastModified: now, changeFrequency: "daily" as const, priority: 0.8 },
    { url: `${SITE_URL}/pricing`, lastModified: now, changeFrequency: "weekly" as const, priority: 0.7 },
  ];
}

export interface BlogSitemapEntry {
  slug: string;
  lastModified: Date;
  changeFrequency?: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  priority?: number;
}

/**
 * Blog/article entries for sitemap. Path = /blog/[slug].
 * When you add a blog: populate this (e.g. from CMS, MD files, or a list).
 */
export function blogSitemapEntries(): MetadataRoute.Sitemap {
  const entries: BlogSitemapEntry[] = [];
  // Example when you have articles:
  // entries.push({ slug: "premier-league-predictions-2025", lastModified: new Date("2025-03-10"), changeFrequency: "monthly", priority: 0.8 });

  return entries.map((e) => ({
    url: `${SITE_URL}/blog/${e.slug}`,
    lastModified: e.lastModified,
    changeFrequency: (e.changeFrequency ?? "monthly") as MetadataRoute.Sitemap[0]["changeFrequency"],
    priority: e.priority ?? 0.7,
  }));
}
