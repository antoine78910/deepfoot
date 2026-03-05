/**
 * Base URL for the backend API.
 * In browser on production (deepfoot.io), if env points to localhost we use the production API
 * so the LP and app work even when NEXT_PUBLIC_API_URL is not set at build time.
 */
const ENV_API_URL = typeof process !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || "") : "";
const DEFAULT_API_URL = ENV_API_URL && ENV_API_URL !== "undefined" ? ENV_API_URL : "http://localhost:8000";

const PRODUCTION_HOSTS = ["www.deepfoot.io", "deepfoot.io"];
const PRODUCTION_API_URL = "https://api.deepfoot.io";

export function getApiUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  const host = window.location?.hostname || "";
  const isProduction = PRODUCTION_HOSTS.some((h) => host === h);
  const isLocalhostOrMissing =
    !DEFAULT_API_URL || DEFAULT_API_URL.includes("localhost") || DEFAULT_API_URL === "undefined";
  if (isProduction && isLocalhostOrMissing) return PRODUCTION_API_URL;
  return DEFAULT_API_URL;
}
