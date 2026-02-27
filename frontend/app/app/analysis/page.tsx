"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnalysisResult } from "@/components/AnalysisResult";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

export default function AppAnalysisPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const { t } = useLanguage();
  const basePath = useAppBasePath();

  useEffect(() => {
    const raw = sessionStorage.getItem("visifoot_analysis");
    if (raw) {
      try {
        setData(JSON.parse(raw));
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
  }, []);

  if (data === null) {
    return (
      <div className="p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          <p className="text-zinc-400 mb-4">{t("analysis.noData")}</p>
          <Link href={`${basePath}/matches`} className="text-accent-cyan hover:underline">{t("history.analyzeMatch")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 pb-16 w-full flex flex-col items-center">
      <div className="w-full max-w-4xl mx-auto">
        <Link href={`${basePath}/matches`} className="inline-block text-zinc-500 hover:text-accent-cyan text-sm mb-8">
          ← {t("analysis.newAnalysis")}
        </Link>
        <AnalysisResult result={data} />
      </div>
    </div>
  );
}
