import { SITE_URL, SITE_NAME, SITE_DESCRIPTION } from "./site";

export interface FAQItem {
  question: string;
  answer: string;
}

/**
 * Organization + WebSite for root layout (global).
 */
export function organizationAndWebSiteSchema(): string {
  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}/#organization`,
        name: SITE_NAME,
        url: SITE_URL,
        description: SITE_DESCRIPTION,
      },
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: SITE_URL,
        name: SITE_NAME,
        description: SITE_DESCRIPTION,
        publisher: { "@id": `${SITE_URL}/#organization` },
        potentialAction: {
          "@type": "SearchAction",
          target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/analyse?home={q}` },
          "query-input": "required name=q",
        },
      },
    ],
  };
  return JSON.stringify(schema);
}

/**
 * FAQPage schema for pages with FAQ sections.
 */
export function faqPageSchema(faq: FAQItem[], pageUrl: string): string {
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faq.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
    url: pageUrl.startsWith("http") ? pageUrl : `${SITE_URL}${pageUrl.startsWith("/") ? pageUrl : `/${pageUrl}`}`,
  };
  return JSON.stringify(schema);
}

/**
 * BreadcrumbList for inner pages.
 */
export function breadcrumbSchema(
  items: { name: string; path: string }[]
): string {
  const schema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: `${SITE_URL}${item.path.startsWith("/") ? item.path : `/${item.path}`}`,
    })),
  };
  return JSON.stringify(schema);
}

/**
 * Article schema for blog posts. Use with buildArticleMetadata.
 */
export function articleSchema(params: {
  headline: string;
  description: string;
  url: string;
  datePublished: string; // ISO 8601
  dateModified?: string;
  authorName?: string;
}): string {
  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: params.headline,
    description: params.description,
    url: params.url.startsWith("http") ? params.url : `${SITE_URL}${params.url.startsWith("/") ? params.url : `/${params.url}`}`,
    datePublished: params.datePublished,
    ...(params.dateModified && { dateModified: params.dateModified }),
    ...(params.authorName && {
      author: {
        "@type": "Person",
        name: params.authorName,
      },
    }),
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL,
    },
  };
  return JSON.stringify(schema);
}

/**
 * SportsEvent for match prediction pages (to use when you have match data).
 */
export function sportsEventSchema(params: {
  name: string;
  startDate: string;
  homeTeam: string;
  awayTeam: string;
  pageUrl: string;
}): string {
  const schema = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: params.name,
    startDate: params.startDate,
    sport: "Soccer",
    competitor: [
      { "@type": "SportsTeam", name: params.homeTeam },
      { "@type": "SportsTeam", name: params.awayTeam },
    ],
    url: params.pageUrl.startsWith("http") ? params.pageUrl : `${SITE_URL}${params.pageUrl.startsWith("/") ? params.pageUrl : `/${params.pageUrl}`}`,
  };
  return JSON.stringify(schema);
}
