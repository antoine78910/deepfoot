"use client";

import { useLanguage } from "@/contexts/LanguageContext";
import { useGeoCurrency } from "@/hooks/useGeoCurrency";
import { formatPrice } from "@/lib/geoCurrency";

const PRO_FEATURE_KEYS = [
  "pricing.featureUnlimited",
  "pricing.featureFullAnalysis",
  "pricing.featureScenarios",
  "pricing.featureStats",
  "pricing.featureNews",
  "pricing.featurePersonalAI",
] as const;

const LIFETIME_FEATURE_KEYS = [
  "pricing.lifetimeUnlimited",
  "pricing.featureFullAnalysis",
  "pricing.featureScenarios",
  "pricing.lifetimeNoPayments",
  "pricing.lifetimePriority",
  "pricing.lifetimeUnlimitedAI",
] as const;

export default function PricingPage() {
  const { t } = useLanguage();
  const { config: currencyConfig, isLoading } = useGeoCurrency();

  return (
    <div className="w-full px-4 pt-4 pb-8 sm:px-6 sm:pt-6 sm:pb-10 max-w-4xl mx-auto">
      <h1 className="text-2xl sm:text-3xl font-bold text-white text-center">
        {t("pricing.title")}
      </h1>
      <p className="text-zinc-400 text-center mt-2 text-sm sm:text-base">
        {t("pricing.subtitle")}
      </p>

      <div className="flex justify-center mt-4">
        <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-500/60 text-emerald-400 text-sm">
          <span className="text-emerald-400">✓</span>
          {t("pricing.starterActive")}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8 sm:mt-10">
        {/* Pro */}
        <div className="relative rounded-2xl bg-dark-card border border-dark-border p-5 sm:p-6 flex flex-col h-full">
          <div className="absolute top-4 right-4">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium">
              ★ {t("pricing.popular")}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xl">👑</span>
            <h2 className="text-xl font-bold text-white">{t("pricing.pro")}</h2>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.proAmount)}
            </span>
            <span className="text-zinc-500 text-sm">{currencyConfig.proSuffix}</span>
          </div>
          <p className="text-zinc-400 text-sm mt-1">{t("pricing.proDesc")}</p>
          <ul className="mt-6 space-y-3 flex-1">
            {PRO_FEATURE_KEYS.map((key, i) => (
              <li key={key} className="flex items-start gap-2 text-sm text-zinc-300">
                <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
                <span>
                  {key === "pricing.featurePersonalAI" ? (
                    <> {t("pricing.featurePersonalAI")} <span className="opacity-70">(1 {t("pricing.perDay")})</span> </>
                  ) : (
                    t(key)
                  )}
                </span>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-6 w-full py-3 px-4 rounded-xl font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 transition"
          >
            {t("pricing.upgradePro")}
          </button>
        </div>

        {/* Lifetime */}
        <div className="relative rounded-2xl bg-dark-card border border-dark-border p-5 sm:p-6 flex flex-col h-full">
          <div className="absolute top-4 right-4">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 text-xs font-medium">
              ∞ {t("pricing.forLife")}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xl">∞</span>
            <h2 className="text-xl font-bold text-white">{t("pricing.lifetime")}</h2>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}
            </span>
            <span className="text-zinc-500 text-sm">{currencyConfig.lifetimeSuffix}</span>
          </div>
          <p className="text-emerald-400 text-sm font-medium mt-2">
            {currencyConfig.saveText}
          </p>
          <ul className="mt-4 space-y-3 flex-1">
            {LIFETIME_FEATURE_KEYS.map((key) => (
              <li key={key} className="flex items-start gap-2 text-sm text-zinc-300">
                <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
                <span>{t(key)}</span>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-6 w-full py-3 px-4 rounded-xl font-medium text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 transition"
          >
            {t("pricing.upgradeLifetime")}
          </button>
        </div>
      </div>
    </div>
  );
}
