import { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo/site";

/**
 * Sitemap of key pages for AI crawlers and discovery.
 * Linked from robots.txt; keep high-value editorial and comparison pages.
 */
export default function aiSitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE_URL, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/ai-football-predictions`, lastModified: now, changeFrequency: "weekly", priority: 0.95 },
    { url: `${SITE_URL}/how-ai-football-predictions-work`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${SITE_URL}/compare/deepfoot-vs-visifoot`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${SITE_URL}/alternatives/visifoot-alternative`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${SITE_URL}/analyse`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/app`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE_URL}/matches`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/pricing`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
  ];
}
