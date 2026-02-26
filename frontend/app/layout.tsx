import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Visifoot 2.0 — Match analysis",
  description: "AI-powered football match predictions: 1X2, Over/Under, BTTS, exact score.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="antialiased min-h-screen bg-dark-bg text-zinc-200">
        {children}
      </body>
    </html>
  );
}
