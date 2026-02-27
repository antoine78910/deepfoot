"use client";

import { useSearchParams } from "next/navigation";
import { MatchInput } from "@/components/MatchInput";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

export default function MatchesPage() {
  const { t } = useLanguage();
  const basePath = useAppBasePath();
  const searchParams = useSearchParams();
  const home = searchParams.get("home") ?? "";
  const away = searchParams.get("away") ?? "";

  return (
    <div className="p-8 w-full flex flex-col items-center">
      <div className="w-full max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-white text-center">{t("matches.title")}</h1>
        <p className="text-zinc-500 mt-1 text-center">{t("matches.subtitle")}</p>
        <p className="text-[#00ffe8] text-xs sm:text-sm mt-1 max-w-2xl mx-auto text-center whitespace-nowrap overflow-hidden text-ellipsis">
          Our AI is connected to football news and crosses millions of data points for each prediction.
        </p>
        <div className="mt-8">
          <MatchInput redirectTo={`${basePath}/analysis`} initialHome={home} initialAway={away} />
        </div>
      </div>
    </div>
  );
}
