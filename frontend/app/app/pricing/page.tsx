"use client";

import { useLanguage } from "@/contexts/LanguageContext";
import { useGeoCurrency } from "@/hooks/useGeoCurrency";
import { formatPrice } from "@/lib/geoCurrency";
import { getWhopCheckoutUrl } from "@/lib/whopCheckout";
import { getUserFromStorage } from "@/lib/auth";

export default function PricingPage() {
  const { t } = useLanguage();
  const { config: currencyConfig, isLoading } = useGeoCurrency();
  const user = getUserFromStorage();
  const currentPlan = user?.plan ?? "free";

  return (
    <div className="w-full px-4 pt-6 pb-12 sm:px-6 sm:pt-8 sm:pb-16 max-w-6xl mx-auto">
      <h1 className="text-2xl sm:text-3xl font-bold text-white text-center">
        {t("pricing.choosePlan")}
      </h1>
      <p className="text-zinc-400 text-center mt-2 text-sm sm:text-base">
        {t("pricing.accessSubtitle")}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-5 mt-8 sm:mt-10">
        {/* Starter */}
        <div className="relative rounded-2xl bg-[#14141c] border border-zinc-600/60 p-5 sm:p-6 flex flex-col transition-all duration-300">
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xl">⚡</span>
            <h2 className="text-xl font-bold text-white">{t("pricing.starter")}</h2>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.starterAmount)}
            </span>
            <span className="text-zinc-500 text-sm">{currencyConfig.starterSuffix}</span>
          </div>
          <p className="text-zinc-400 text-sm mt-1">{t("pricing.starterDesc")}</p>
          <ul className="mt-6 space-y-3 flex-1">
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.starterFeature1")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.starterFeatureReduced")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.starterFeatureKeyStats")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.starterFeatureExactProb")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-red-400 mt-0.5 flex-shrink-0">✕</span>
              <span className="text-zinc-500">{t("pricing.starterNoAI")}</span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => {
              window.location.href = getWhopCheckoutUrl("starter", currencyConfig.currency);
            }}
            className="mt-6 w-full py-3 px-4 rounded-xl font-semibold text-[#0d0d12] bg-[#00ffe8] hover:bg-[#00ffe8]/90 transition-all duration-300 disabled:opacity-50"
            disabled={currentPlan === "starter"}
          >
            {currentPlan === "starter"
              ? t("pricing.currentPlan")
              : `${t("pricing.unlockStarter")} - ${formatPrice(currencyConfig, currencyConfig.starterAmount)}${t("pricing.perMonth")}`}
          </button>
        </div>

        {/* Pro - Popular */}
        <div className="relative rounded-2xl bg-[#14141c] border-2 border-[#00ffe8]/60 p-5 sm:p-6 flex flex-col transition-all duration-300 shadow-[0_0_30px_-5px_rgba(0,255,232,0.25)] hover:shadow-[0_0_40px_-5px_rgba(0,255,232,0.35)]">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center gap-1 px-3 py-1 rounded-full bg-[#00ffe8]/20 border border-[#00ffe8]/50 text-[#00ffe8] text-xs font-medium">
            <span>★</span> <span>★</span> {t("pricing.popular")}
          </div>
          <div className="flex items-center gap-2 mt-2">
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
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-[#00ffe8] mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureUnlimited")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-[#00ffe8] mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureFullAnalysis")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-[#00ffe8] mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureScenarios")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-[#00ffe8] mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureStats")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-[#00ffe8] mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureNews")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
              <span>
                {t("pricing.featurePersonalAI")} <span className="opacity-70">(1 {t("pricing.perDay")})</span>
                <span className="ml-1 opacity-70" title="AI">💬</span>
              </span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => {
              window.location.href = getWhopCheckoutUrl("pro", currencyConfig.currency);
            }}
            className="mt-6 w-full py-3 px-4 rounded-xl font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 transition disabled:opacity-50"
            disabled={currentPlan === "pro"}
          >
            {currentPlan === "pro"
              ? t("pricing.currentPlan")
              : `${t("pricing.unlockPro")} - ${formatPrice(currencyConfig, currencyConfig.proAmount)}${t("pricing.perMonth")}`}
          </button>
        </div>

        {/* Lifetime - For life */}
        <div className="relative rounded-2xl bg-[#14141c] border-2 border-amber-500/60 p-5 sm:p-6 flex flex-col transition-all duration-300 shadow-[0_0_30px_-5px_rgba(245,158,11,0.2)] hover:shadow-[0_0_45px_-5px_rgba(245,158,11,0.35)]">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-medium">
            <span>∞</span> {t("pricing.forLife")}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xl">∞</span>
            <h2 className="text-xl font-bold text-white">{t("pricing.lifetime")}</h2>
          </div>
          <div className="mt-4 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-amber-400">
              {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}
            </span>
            <span className="text-zinc-500 text-sm">{currencyConfig.lifetimeSuffix}</span>
          </div>
          <p className="text-emerald-400 text-sm font-medium mt-2">{currencyConfig.saveText}</p>
          <ul className="mt-4 space-y-3 flex-1">
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.lifetimeUnlimited")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureFullAnalysis")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.featureScenarios")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.lifetimeNoPayments")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>{t("pricing.lifetimePriority")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">✓</span>
              <span>
                <strong className="font-semibold text-amber-200/95">{t("pricing.lifetimeUnlimitedAI")}</strong>
                <span className="ml-1" title="AI">💬</span>
              </span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => {
              window.location.href = getWhopCheckoutUrl("lifetime", currencyConfig.currency);
            }}
            className="mt-6 w-full py-3 px-4 rounded-xl font-semibold text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 transition-all duration-300 disabled:opacity-50 shadow-[0_0_20px_-5px_rgba(245,158,11,0.4)]"
            disabled={currentPlan === "lifetime"}
          >
            {currentPlan === "lifetime"
              ? t("pricing.currentPlan")
              : `${t("pricing.unlockLifetime")} - ${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}`}
          </button>
        </div>
      </div>

      <p className="text-zinc-500 text-center text-sm mt-10 max-w-2xl mx-auto">
        {t("pricing.footerDisclaimer")}
      </p>
      <p className="text-zinc-500 text-center text-sm mt-3">
        {t("pricing.footerContact")}{" "}
        <a href="mailto:app@deepfoot.io" className="text-[#00ffe8] hover:underline">
          app@deepfoot.io
        </a>
      </p>
    </div>
  );
}
