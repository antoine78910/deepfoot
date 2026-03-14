import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { ClientProviders } from "@/components/ClientProviders";
import { SITE_URL, SITE_NAME, SITE_DESCRIPTION } from "@/lib/seo/site";
import { organizationAndWebSiteSchema } from "@/lib/seo/schema";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "DeepFoot – AI Football Predictions",
    template: "%s | DeepFoot",
  },
  description: SITE_DESCRIPTION,
  keywords: [
    "football predictions",
    "AI predictions",
    "match analysis",
    "football AI",
    "soccer predictions",
    "DeepFoot",
    "deepfoot.ai",
    "AI football prediction",
    "visifoot alternative",
  ],
  authors: [{ name: SITE_NAME, url: SITE_URL }],
  creator: SITE_NAME,
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: "DeepFoot – AI Football Predictions",
    description: "AI-powered football match predictions: 1X2, Over/Under, BTTS, exact score and scenario analysis.",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "DeepFoot – AI Football Predictions",
    description: "AI-powered football match predictions for every match.",
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/favicon.png",
    apple: "/favicon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
  const supabaseEnvScript =
    supabaseUrl && supabaseAnonKey
      ? `window.__SUPABASE_ENV__={url:${JSON.stringify(supabaseUrl)},anonKey:${JSON.stringify(supabaseAnonKey)}};`
      : "";

  const jsonLd = organizationAndWebSiteSchema();

  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased min-h-screen bg-app-gradient text-zinc-200">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLd }}
        />
        {supabaseEnvScript ? (
          <script
            dangerouslySetInnerHTML={{ __html: supabaseEnvScript }}
          />
        ) : null}
        <ClientProviders>{children}</ClientProviders>
        <script
          id="datafast-queue"
          dangerouslySetInnerHTML={{
            __html: `window.datafast = window.datafast || function() { (window.datafast.q = window.datafast.q || []).push(arguments); };`,
          }}
        />
        <Script
          src="https://datafa.st/js/script.js"
          data-website-id="dfid_hXUwdw1eEOt3xICr0vj4y"
          data-domain="deepfoot.io"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
