/**
 * Shared Sentry runtime options.
 * Event volume is capped here so client, server, and edge stay aligned.
 * The DSN is public by design (it ships in the browser bundle). The auth token
 * used to upload source maps must stay in the environment, never in git.
 */

import type { TracesSamplerSamplingContext } from "@sentry/core";

const STATIC_EXTENSION = /\.(?:svg|png|jpe?g|gif|webp|ico|css|js|map|txt|woff2?)$/i;

const HEALTH_CHECK =
  /^(?:\/api)?\/(?:health|healthz|readyz|livez|ready|live|ping)(?:\/|$)/i;

function isIgnoredTracePath(path: string): boolean {
  if (path === "/monitoring" || path.startsWith("/monitoring/")) return true;
  if (path === "/_next/static" || path.startsWith("/_next/static/")) return true;
  if (path === "/_next/image" || path.startsWith("/_next/image/")) return true;
  if (path === "/favicon.ico" || path === "/robots.txt") return true;
  if (HEALTH_CHECK.test(path)) return true;
  return STATIC_EXTENSION.test(path);
}

/** Production trace sample rate. Noisy routes are dropped before this rate applies. */
const PRODUCTION_TRACE_SAMPLE_RATE = 0.05;

function pathnameOf(raw: string): string {
  const trimmed = raw.trim();
  const withMethod = trimmed.match(
    /^(?:middleware\s+)?(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)/i,
  );
  const candidate = withMethod?.[1] ?? trimmed;
  if (candidate.startsWith("http://") || candidate.startsWith("https://")) {
    try {
      return new URL(candidate).pathname || "/";
    } catch {
      return candidate;
    }
  }
  const path = (candidate.split("?")[0] || candidate).trim();
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

function traceTargets(samplingContext: TracesSamplerSamplingContext): string[] {
  const targets: string[] = [];
  if (samplingContext.name) targets.push(samplingContext.name);
  if (samplingContext.location?.pathname) targets.push(samplingContext.location.pathname);
  if (samplingContext.normalizedRequest?.url) targets.push(samplingContext.normalizedRequest.url);

  const attributes = samplingContext.attributes;
  if (attributes) {
    for (const key of ["http.target", "http.route", "url.path", "url.full", "http.url"]) {
      const value = attributes[key];
      if (typeof value === "string" && value) targets.push(value);
    }
  }
  return targets;
}

/** Drop tunnel, static, and health-check spans. Sample everything else at 5% in production. */
export function tracesSampler(samplingContext: TracesSamplerSamplingContext): number {
  if (process.env.NODE_ENV !== "production") return 0;

  for (const target of traceTargets(samplingContext)) {
    if (isIgnoredTracePath(pathnameOf(target))) return 0;
  }

  return samplingContext.inheritOrSampleWith(PRODUCTION_TRACE_SAMPLE_RATE);
}

/** Browser-extension and benign client noise. Safe on server and edge as well. */
export const sentryIgnoreErrors: Array<string | RegExp> = [
  "ResizeObserver loop limit exceeded",
  "ResizeObserver loop completed with undelivered notifications",
  /^ResizeObserver loop/i,
  "Non-Error promise rejection captured",
  "Non-Error exception captured",
  /^Script error\.?$/,
  "AbortError",
  "The operation was aborted",
  "The user aborted a request",
  "NetworkError when attempting to fetch resource",
  "Failed to fetch",
  "Load failed",
  "ChunkLoadError",
  /chrome-extension:/i,
  /moz-extension:/i,
  /safari-extension:/i,
  /safari-web-extension:/i,
];

/** Script URLs that should never open a Sentry issue (extensions and injected plugins). */
export const sentryDenyUrls: Array<string | RegExp> = [
  /^chrome:\/\//i,
  /^chrome-extension:\/\//i,
  /^moz-extension:\/\//i,
  /^safari-extension:\/\//i,
  /^safari-web-extension:\/\//i,
  /^resource:\/\//i,
  /extensions\//i,
  /graph\.facebook\.com/i,
  /connect\.facebook\.net/i,
  /127\.0\.0\.1:4001\/isrunning/i,
];

export function sentryBaseOptions() {
  return {
    dsn: "https://562edb866da66072555bae80427821f9@o4510985108455424.ingest.de.sentry.io/4510985110093905",
    enabled: process.env.NODE_ENV === "production",
    enableLogs: false,
    sendDefaultPii: false,
    tracesSampler,
    ignoreErrors: sentryIgnoreErrors,
    denyUrls: sentryDenyUrls,
  };
}
