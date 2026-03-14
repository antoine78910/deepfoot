import { MetadataRoute } from "next";
import { staticSitemapEntries, blogSitemapEntries } from "@/lib/seo/sitemap-pages";

/**
 * Main sitemap: https://deepfoot.ai/sitemap.xml
 * Submit this URL in Google Search Console (and Bing).
 * Combines static pages + blog articles (see lib/seo/sitemap-pages.ts).
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [...staticSitemapEntries(), ...blogSitemapEntries()];
}
