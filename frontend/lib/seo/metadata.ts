import type { Metadata } from "next";
import { SITE_URL, SITE_NAME } from "./site";

export interface PageMetaInput {
  title: string;
  description: string;
  path: string;
  noIndex?: boolean;
  openGraph?: { title?: string; description?: string };
}

/** For blog/articles: path = /blog/my-slug, optional publishedTime for OG. */
export interface ArticleMetaInput extends PageMetaInput {
  publishedTime?: string; // ISO 8601 e.g. "2025-03-10T12:00:00Z"
  modifiedTime?: string;
  authors?: string[];
}

/**
 * Build Next.js Metadata for a page. Title gets " | DeepFoot" appended by template.
 * Use title without suffix; keep total length ≤ 60 chars for title part.
 */
export function buildPageMetadata(input: PageMetaInput): Metadata {
  const canonical = `${SITE_URL}${input.path.startsWith("/") ? input.path : `/${input.path}`}`;
  const ogTitle = input.openGraph?.title ?? input.title;
  const ogDesc = input.openGraph?.description ?? input.description;

  return {
    title: input.title,
    description: input.description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      url: canonical,
      siteName: SITE_NAME,
      title: ogTitle,
      description: ogDesc,
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description: ogDesc,
    },
    robots: input.noIndex
      ? { index: false, follow: true }
      : { index: true, follow: true },
  };
}

/**
 * Build metadata for a blog/article page. Sets canonical and OG type "article".
 * Canonical URL = SITE_URL + path (e.g. path = "/blog/premier-league-predictions-2025").
 */
export function buildArticleMetadata(input: ArticleMetaInput): Metadata {
  const path = input.path.startsWith("/") ? input.path : `/${input.path}`;
  const canonical = `${SITE_URL}${path}`;
  const ogTitle = input.openGraph?.title ?? input.title;
  const ogDesc = input.openGraph?.description ?? input.description;

  return {
    title: input.title,
    description: input.description,
    alternates: { canonical },
    openGraph: {
      type: "article",
      url: canonical,
      siteName: SITE_NAME,
      title: ogTitle,
      description: ogDesc,
      locale: "en_US",
      ...(input.publishedTime && { publishedTime: input.publishedTime }),
      ...(input.modifiedTime && { modifiedTime: input.modifiedTime }),
      ...(input.authors?.length && { authors: input.authors }),
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description: ogDesc,
    },
    robots: input.noIndex
      ? { index: false, follow: true }
      : { index: true, follow: true },
  };
}
