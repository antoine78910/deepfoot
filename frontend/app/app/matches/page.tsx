"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MatchInput } from "@/components/MatchInput";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

function MatchesContent() {
  const { t } = useLanguage();
  const basePath = useAppBasePath();
  const searchParams = useSearchParams();
  const home = searchParams.get("home") ?? "";
  const away = searchParams.get("away") ?? "";
  const [useApiPredictions, setUseApiPredictions] = useState(false);

  return (
    <div className="p-8 w-full flex flex-col items-center">
      <div className="w-full max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-white text-center">{t("matches.title")}</h1>
        <p className="text-zinc-500 mt-1 text-center">{t("matches.subtitle")}</p>
        <p className="text-[#00ffe8] text-xs sm:text-sm mt-1 max-w-2xl mx-auto text-center whitespace-nowrap overflow-hidden text-ellipsis">
          Our AI is connected to football news and crosses millions of data points for each prediction.
        </p>
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-2 text-zinc-400 text-sm">
          <span className="font-medium">Modèle de prédiction (test):</span>
          <select
            value={useApiPredictions ? "api" : "our_model"}
            onChange={(e) => setUseApiPredictions(e.target.value === "api")}
            className="bg-zinc-800 border border-zinc-600 rounded px-3 py-1.5 text-white focus:ring-1 focus:ring-[#00ffe8] focus:border-[#00ffe8] outline-none"
          >
            <option value="our_model">Notre modèle (Poisson)</option>
            <option value="api">API-Football Predictions</option>
          </select>
        </div>
        <div className="mt-8">
          <MatchInput
            redirectTo={`${basePath}/analysis`}
            initialHome={home}
            initialAway={away}
            useApiPredictions={useApiPredictions}
          />
        </div>
      </div>
    </div>
  );
}

export default function MatchesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-zinc-400 text-center">Loading...</div>}>
      <MatchesContent />
    </Suspense>
  );
}
