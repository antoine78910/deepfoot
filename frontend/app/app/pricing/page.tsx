"use client";

import { useState } from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useGeoCurrency } from "@/hooks/useGeoCurrency";
import { formatPrice } from "@/lib/geoCurrency";
import { getWhopCheckoutUrl, getDatafastVisitorId, isUpgradeFromCurrentPlan, getWhopManageUrl } from "@/lib/whopCheckout";
import type { WhopPlanId } from "@/lib/whopCheckout";
import { getUserFromStorage } from "@/lib/auth";
import { getApiUrl } from "@/lib/api";
import { trackDatafastGoal } from "@/lib/datafast";
import { Medal, Check, Gem } from "lucide-react";

const ACCENT = "#00ffe8";

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className ?? ""}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

function LightningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
    </svg>
  );
}

function CrownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z" />
      <path d="M5 21h14" />
    </svg>
  );
}

function InfinityIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z" />
    </svg>
  );
}

function MedalIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M8 3v3M16 3v3" />
      <path d="M12 7v7M11 14h2" />
    </svg>
  );
}

function PricingPage() {
  const { t } = useLanguage();
  const { config: currencyConfig, isLoading } = useGeoCurrency();
  const user = getUserFromStorage();
  const currentPlan = (user && user.plan) ? user.plan : "free";
  const [loadingPlan, setLoadingPlan] = useState<WhopPlanId | null>(null);

  const goToWhop = async (plan: WhopPlanId, source: string) => {
    if (plan === "starter") trackDatafastGoal("unlock_9");
    else if (plan === "pro") trackDatafastGoal("unlock_19");
    else if (plan === "lifetime") trackDatafastGoal("unlock_99");
    trackDatafastGoal("click_unlock", { source });
    trackDatafastGoal("initiate_checkout", { plan, source });
    setLoadingPlan(plan);
    let url: string;
    if (isUpgradeFromCurrentPlan(currentPlan, plan)) {
      const manageUrl = getWhopManageUrl(user);
      if (manageUrl) {
        url = manageUrl;
      } else if (user?.id) {
        try {
          const r = await fetch(`${getApiUrl()}/me/whop-manage-url`, { headers: { "X-User-Id": user.id } });
          if (r.ok) {
            const data = (await r.json()) as { url?: string };
            if (data?.url) url = data.url;
          }
        } catch {
          // ignore
        }
      }
      if (typeof url === "undefined") {
        url = getWhopCheckoutUrl(plan, currencyConfig.currency, getDatafastVisitorId(), source, user?.email, user?.whop_membership_id ?? undefined);
      }
    } else {
      url = getWhopCheckoutUrl(plan, currencyConfig.currency, getDatafastVisitorId(), source, user?.email, plan !== "starter" ? user?.whop_membership_id : undefined);
    }
    requestAnimationFrame(() => {
      setTimeout(() => {
        window.location.href = url;
      }, 400);
    });
  };

  return (
    <div className="w-full px-4 pt-6 pb-12 sm:px-6 sm:pt-8 sm:pb-16 max-w-4xl mx-auto">
      <h1 className="text-2xl sm:text-3xl font-bold text-white text-center">
        {t("pricing.choosePlan")}
      </h1>
      <p className="text-zinc-400 text-center mt-2 text-sm sm:text-base">
        {t("pricing.accessSubtitle")}
      </p>

      {currentPlan === "lifetime" && (
        <div className="mt-10 sm:mt-12 max-w-lg mx-auto text-center rounded-2xl bg-[#14141c]/70 border-2 border-amber-500/50 p-8 sm:p-10 shadow-[0_0_30px_-5px_rgba(245,158,11,0.15)]">
          <p className="text-2xl sm:text-3xl font-bold text-amber-400">
            {t("pricing.alreadyTopPlan")}
          </p>
          <p className="text-zinc-400 mt-3 text-sm sm:text-base">
            {t("pricing.alreadyTopPlanSub")}
          </p>
        </div>
      )}

      {currentPlan !== "lifetime" && (
        <div className={`grid gap-4 sm:gap-4 mt-8 sm:mt-10 mx-auto ${currentPlan === "starter" ? "grid-cols-1 sm:grid-cols-2 max-w-2xl" : "grid-cols-1 sm:grid-cols-3 max-w-4xl"}`}>
        {/* Starter - only when user is free */}
        {currentPlan === "free" && (
        <div className="relative rounded-2xl bg-[#14141c]/70 border border-zinc-600/50 p-5 sm:p-5 flex flex-col transition-all duration-300 backdrop-blur-sm">
          <div className="flex items-center gap-2 mt-1">
            <span className="w-6 h-6 flex-shrink-0" style={{ color: ACCENT }}>
              <LightningIcon className="w-full h-full" />
            </span>
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
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.starterFeature1")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.starterFeatureReduced")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.starterFeatureKeyStats")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.starterFeatureExactProb")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <span className="text-red-400 mt-0.5 flex-shrink-0">✕</span>
              <span className="text-zinc-500">{t("pricing.starterNoAI")}</span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => goToWhop("starter", "pricing-starter")}
            disabled={loadingPlan !== null}
            className="mt-6 w-full py-3 px-4 rounded-xl font-semibold text-[#00ffe8] bg-transparent border-2 border-[#00ffe8]/50 hover:border-[#00ffe8] hover:shadow-[0_0_20px_4px_rgba(0,255,232,0.45)] transition-all duration-300 disabled:opacity-50 disabled:bg-zinc-800/50 disabled:border-zinc-600 disabled:text-zinc-400 disabled:shadow-none flex items-center justify-center gap-2"
          >
            {loadingPlan === "starter" ? (
              <>
                <Spinner className="w-5 h-5 flex-shrink-0 text-[#00ffe8]" />
                <span>Redirecting...</span>
              </>
            ) : (
              `${t("pricing.unlockStarter")} - ${formatPrice(currencyConfig, currencyConfig.starterAmount)}${t("pricing.perMonth")}`
            )}
          </button>
        </div>
        )}

        {/* Pro - Popular (only when free or starter; if user is pro, only Lifetime is shown) */}
        {(currentPlan === "free" || currentPlan === "starter") && (
        <div className="relative rounded-2xl bg-[#14141c]/70 border-2 border-[#00ffe8]/60 p-5 sm:p-5 flex flex-col transition-all duration-300 backdrop-blur-sm shadow-[0_0_30px_-5px_rgba(0,255,232,0.25)] hover:shadow-[0_0_40px_-5px_rgba(0,255,232,0.35)]">
          <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#00ffe8]/20 border border-[#00ffe8]/50 text-[#00ffe8] text-xs font-medium">
            <Medal className="w-3.5 h-3.5 flex-shrink-0" stroke="currentColor" />
            {t("pricing.popular")}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="w-6 h-6 flex-shrink-0" style={{ color: ACCENT }}>
              <CrownIcon className="w-full h-full" />
            </span>
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
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.featureUnlimited")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.featureFullAnalysis")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.featureScenarios")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.featureStats")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>{t("pricing.featureNews")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Gem className="w-4 h-4 mt-0.5 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
              <span>
                <strong className="font-semibold text-white">{t("pricing.featurePersonalAI")}</strong>
                <span className="opacity-90"> (1 {t("pricing.perDay")})</span>
              </span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => goToWhop("pro", "pricing-pro")}
            disabled={loadingPlan !== null}
            className="mt-6 w-full py-3 px-4 rounded-xl font-semibold text-[#0d0d12] bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:from-[#00ffe8] hover:to-[#00ddcc] hover:shadow-[0_0_24px_6px_rgba(0,255,232,0.5)] transition-all duration-300 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loadingPlan === "pro" ? (
              <>
                <Spinner className="w-5 h-5 flex-shrink-0 text-[#0d0d12]" />
                <span>Redirecting...</span>
              </>
            ) : currentPlan === "starter" ? (
              `${t("pricing.upgradePro")} - ${formatPrice(currencyConfig, currencyConfig.proAmount)}${t("pricing.perMonth")}`
            ) : (
              `${t("pricing.unlockPro")} - ${formatPrice(currencyConfig, currencyConfig.proAmount)}${t("pricing.perMonth")}`
            )}
          </button>
        </div>
        )}

        {/* Lifetime - For life (centered when alone, e.g. user is pro) */}
        <div className={`relative rounded-2xl bg-[#14141c]/70 border-2 border-amber-500/60 p-5 sm:p-5 flex flex-col transition-all duration-300 backdrop-blur-sm shadow-[0_0_30px_-5px_rgba(245,158,11,0.2)] hover:shadow-[0_0_45px_-5px_rgba(245,158,11,0.35)] ${currentPlan === "pro" ? "sm:col-start-2" : ""}`}>
          <div className="absolute top-3 right-3 flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-medium">
            <span className="w-3.5 h-3.5 flex-shrink-0 inline-block" style={{ color: "currentColor" }}>
              <InfinityIcon className="w-full h-full" />
            </span>
            {t("pricing.forLife")}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="w-6 h-6 flex-shrink-0 text-amber-400">
              <InfinityIcon className="w-full h-full" />
            </span>
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
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>{t("pricing.lifetimeUnlimited")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>{t("pricing.featureFullAnalysis")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>{t("pricing.featureScenarios")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>{t("pricing.lifetimeNoPayments")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>{t("pricing.lifetimePriority")}</span>
            </li>
            <li className="flex items-start gap-2 text-sm text-zinc-300">
              <Gem className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
              <span>
                <strong className="font-semibold text-amber-200/95">{t("pricing.lifetimeUnlimitedAI")}</strong>
              </span>
            </li>
          </ul>
          <button
            type="button"
            onClick={() => goToWhop("lifetime", "pricing-lifetime")}
            disabled={loadingPlan !== null}
            className="mt-6 w-full py-3 px-4 rounded-xl font-semibold text-[#0d0d12] bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 hover:shadow-[0_0_22px_6px_rgba(245,158,11,0.45)] transition-all duration-300 disabled:opacity-50 disabled:text-zinc-500 shadow-[0_0_20px_-5px_rgba(245,158,11,0.4)] flex items-center justify-center gap-2"
          >
            {loadingPlan === "lifetime" ? (
              <>
                <Spinner className="w-5 h-5 flex-shrink-0 text-[#0d0d12]" />
                <span>Redirecting...</span>
              </>
            ) : currentPlan === "starter" || currentPlan === "pro" ? (
              `${t("pricing.upgradeLifetime")} - ${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}`
            ) : (
              `${t("pricing.unlockLifetime")} - ${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}`
            )}
          </button>
        </div>
        </div>
      )}

      {loadingPlan !== null && user?.email && (
        <p className="text-zinc-400 text-center text-xs mt-6 max-w-xl mx-auto">
          {t("checkout.emailNotice").replace("{email}", user.email)}
        </p>
      )}
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

export default PricingPage;
