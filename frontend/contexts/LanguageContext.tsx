"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Lang, t as tFn } from "@/lib/translations";

const STORAGE_KEY = "visifoot_lang";

const LanguageContext = createContext<{
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
} | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as Lang | null;
      if (stored === "en" || stored === "fr") setLangState(stored);
    } catch {
      // ignore
    }
    setMounted(true);
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
      if (typeof document !== "undefined") document.documentElement.lang = l;
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (mounted && typeof document !== "undefined") document.documentElement.lang = lang;
  }, [lang, mounted]);

  const t = useCallback((key: string) => tFn(lang, key), [lang]);

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
