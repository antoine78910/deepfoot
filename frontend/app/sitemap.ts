import { MetadataRoute } from "next";

const BASE = "https://deepfoot.ai";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE, lastModified: new Date(), changeFrequency: "daily", priority: 1 },
    { url: `${BASE}/analyse`, lastModified: new Date(), changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE}/app`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE}/app/matches`, lastModified: new Date(), changeFrequency: "daily", priority: 0.8 },
    { url: `${BASE}/app/pricing`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.7 },
  ];
}
