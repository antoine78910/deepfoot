"use client";

import { LanguageProvider } from "@/contexts/LanguageContext";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}
