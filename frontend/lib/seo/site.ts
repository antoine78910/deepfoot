/**
 * Single source of truth for canonical host and brand.
 * Used by layout, sitemaps, robots, metadata, and schema.
 */
export const SITE_URL = "https://deepfoot.ai";
export const SITE_NAME = "DeepFoot";
export const SITE_DESCRIPTION =
  "AI-powered football match predictions. Get 1X2, Over/Under, BTTS, exact scores and scenario analysis for every match.";

export function absoluteUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}${p}`;
}
