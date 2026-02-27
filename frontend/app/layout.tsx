import type { Metadata } from "next";
import "./globals.css";
import { ClientProviders } from "@/components/ClientProviders";

const SITE_URL = "https://deepfoot.ai";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "DeepFoot – AI Football Predictions",
    template: "%s | DeepFoot",
  },
  description:
    "AI-powered football match predictions. Get 1X2, Over/Under, BTTS, exact scores and scenario analysis for every match. DeepFoot – AI Football Predictions.",
  keywords: [
    "football predictions",
    "AI predictions",
    "match analysis",
    "football AI",
    "soccer predictions",
    "DeepFoot",
    "deepfoot.ai",
  ],
  authors: [{ name: "DeepFoot", url: SITE_URL }],
  creator: "DeepFoot",
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "DeepFoot",
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
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased min-h-screen bg-app-gradient text-zinc-200">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
