"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "@/contexts/LanguageContext";
import { useGeoCurrency } from "@/hooks/useGeoCurrency";
import { formatPrice } from "@/lib/geoCurrency";
import { getWhopCheckoutUrl, getDatafastVisitorId } from "@/lib/whopCheckout";
import { trackDatafastGoal } from "@/lib/datafast";
import type { WhopPlanId } from "@/lib/whopCheckout";
import { getUserFromStorage } from "@/lib/auth";
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

export type PricingModalVariant = "all" | "pro_lifetime" | "free";

export function UnlockPricingModal({
  open,
  onClose,
  variant = "all",
}: {
  open: boolean;
  onClose: () => void;
  /** "pro_lifetime" = only Pro + Lifetime (e.g. starter limit); "free" = 3 offers with free-limit copy; "all" = default 3 offers */
  variant?: PricingModalVariant;
}) {
  const { t } = useLanguage();
  const { config: currencyConfig, isLoading } = useGeoCurrency();
  const user = getUserFromStorage();
  const currentPlan = user?.plan ?? "free";
  const onlyProLifetime = variant === "pro_lifetime";
  const title = onlyProLifetime ? t("limitModal.starterTitle") : variant === "free" ? t("limitModal.freeTitle") : t("unlockModal2.title");
  const subtitle = onlyProLifetime ? t("limitModal.starterSubtitle") : variant === "free" ? t("limitModal.freeSubtitle") : t("unlockModal2.subtitle");
  const [loadingPlan, setLoadingPlan] = useState<WhopPlanId | null>(null);

  const goToWhop = (plan: WhopPlanId, source: string) => {
    if (plan === "starter") trackDatafastGoal("unlock_9");
    else if (plan === "pro") trackDatafastGoal("unlock_19");
    else if (plan === "lifetime") trackDatafastGoal("unlock_99");
    trackDatafastGoal("initiate_checkout", { plan, source });
    setLoadingPlan(plan);
    const url = getWhopCheckoutUrl(
      plan,
      currencyConfig.currency,
      getDatafastVisitorId(),
      source,
      user?.email,
      plan !== "starter" ? user?.whop_membership_id : undefined
    );
    requestAnimationFrame(() => {
      setTimeout(() => {
        window.location.href = url;
      }, 400);
    });
  };

  useEffect(() => {
    if (!open) return;
    const onEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onEscape);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const modal = (
    <div className="fixed inset-0 z-[101] flex items-center justify-center p-4 bg-black/30 backdrop-blur-lg">
      <div
        className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#101217]/90 border border-white/10 shadow-2xl backdrop-blur-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pricing-modal-title"
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 p-6 pb-4 bg-[#101217]/95 border-b border-white/5 backdrop-blur-sm">
          <div>
            <h2 id="pricing-modal-title" className="text-xl sm:text-2xl font-bold text-white">
              {title}
            </h2>
            <p className="text-sm text-zinc-400 mt-1">{subtitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition flex-shrink-0"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 pt-4">
          <div className={`grid grid-cols-1 gap-4 ${onlyProLifetime ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
            {/* Starter - hidden when onlyProLifetime */}
            {!onlyProLifetime && (
            <div className="rounded-xl bg-[#14141c] border border-zinc-600/60 p-5 flex flex-col">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 flex-shrink-0" style={{ color: ACCENT }}>
                  <LightningIcon className="w-full h-full" />
                </span>
                <h3 className="text-lg font-bold text-white">{t("pricing.starter")}</h3>
              </div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-white">
                  {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.starterAmount)}
                </span>
                <span className="text-zinc-500 text-sm">{currencyConfig.starterSuffix}</span>
              </div>
              <ul className="mt-4 space-y-2 flex-1 text-sm text-zinc-300">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.starterFeature1")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.starterFeatureReduced")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.starterFeatureKeyStats")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.starterFeatureExactProb")}
                </li>
              </ul>
              <button
                type="button"
                onClick={() => goToWhop("starter", "modal-starter")}
                disabled={currentPlan === "starter" || loadingPlan !== null}
                className="mt-4 w-full py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-300 disabled:opacity-50 disabled:bg-zinc-800/50 disabled:border-zinc-600 disabled:text-zinc-400 disabled:shadow-none bg-transparent border-2 border-[#00ffe8]/50 hover:border-[#00ffe8] text-[#00ffe8] hover:shadow-[0_0_18px_4px_rgba(0,255,232,0.45)] flex items-center justify-center gap-2"
              >
                {loadingPlan === "starter" ? (
                  <>
                    <Spinner className="w-5 h-5 flex-shrink-0" />
                    <span>Redirecting...</span>
                  </>
                ) : currentPlan === "starter" ? (
                  t("pricing.currentPlan")
                ) : (
                  `${t("pricing.unlockStarter")} - ${formatPrice(currencyConfig, currencyConfig.starterAmount)}${t("pricing.perMonth")}`
                )}
              </button>
            </div>
            )}

            {/* Pro - Popular */}
            <div className="relative rounded-xl bg-[#14141c]/70 border-2 flex flex-col p-4 backdrop-blur-sm" style={{ borderColor: `${ACCENT}70` }}>
              <div
                className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium text-[#00ffe8]"
                style={{ background: `${ACCENT}25`, border: `1px solid ${ACCENT}50` }}
              >
                <Medal className="w-3.5 h-3.5 flex-shrink-0" stroke="currentColor" />
                {t("pricing.popular")}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-6 h-6 flex-shrink-0" style={{ color: ACCENT }}>
                  <CrownIcon className="w-full h-full" />
                </span>
                <h3 className="text-lg font-bold text-white">{t("pricing.pro")}</h3>
              </div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-white">
                  {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.proAmount)}
                </span>
                <span className="text-zinc-500 text-sm">{currencyConfig.proSuffix}</span>
              </div>
              <p className="text-zinc-400 text-xs mt-0.5">{t("pricing.proDesc")}</p>
              <ul className="mt-3 space-y-2 flex-1 text-sm text-zinc-300">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.featureUnlimited")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.featureFullAnalysis")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> {t("pricing.featureScenarios")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} /> Advanced stats + news
                </li>
                <li className="flex items-center gap-2">
                  <Gem className="w-4 h-4 flex-shrink-0 text-[#00ffe8]" strokeWidth={2.5} />
                  <span>{t("pricing.featurePersonalAI")} (1 {t("pricing.perDay")})</span>
                </li>
              </ul>
              <button
                type="button"
                onClick={() => goToWhop("pro", "modal-pro")}
                disabled={currentPlan === "pro" || loadingPlan !== null}
                className="mt-4 w-full py-2.5 px-4 rounded-xl font-semibold text-[#0d0d12] text-sm transition-all duration-300 disabled:opacity-50 hover:shadow-[0_0_20px_5px_rgba(0,255,232,0.5)] flex items-center justify-center gap-2"
                style={{ background: `linear-gradient(135deg, ${ACCENT} 0%, #6FE7C0 100%)` }}
              >
                {loadingPlan === "pro" ? (
                  <>
                    <Spinner className="w-5 h-5 flex-shrink-0 text-[#0d0d12]" />
                    <span>Redirecting...</span>
                  </>
                ) : currentPlan === "pro" ? (
                  t("pricing.currentPlan")
                ) : currentPlan === "starter" ? (
                  `${t("pricing.upgradePro")} - ${formatPrice(currencyConfig, currencyConfig.proAmount)}${t("pricing.perMonth")}`
                ) : (
                  `${t("pricing.unlockPro")} - ${formatPrice(currencyConfig, currencyConfig.proAmount)}${t("pricing.perMonth")}`
                )}
              </button>
            </div>

            {/* Lifetime */}
            <div className="relative rounded-xl bg-[#14141c]/70 border-2 border-amber-500/60 p-4 flex flex-col backdrop-blur-sm">
              <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-medium">
                <span className="w-3.5 h-3.5 flex-shrink-0 inline-block text-amber-400">
                  <InfinityIcon className="w-full h-full" />
                </span>
                {t("pricing.forLife")}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-6 h-6 flex-shrink-0 text-amber-400">
                  <InfinityIcon className="w-full h-full" />
                </span>
                <h3 className="text-lg font-bold text-white">{t("pricing.lifetime")}</h3>
              </div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-amber-400">
                  {isLoading ? "—" : formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}
                </span>
                <span className="text-zinc-500 text-sm">{currencyConfig.lifetimeSuffix}</span>
              </div>
              <p className="text-[#00ffe8] text-xs font-medium mt-1">{currencyConfig.saveText}</p>
              <ul className="mt-3 space-y-2 flex-1 text-sm text-zinc-300">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("pricing.lifetimeUnlimited")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("pricing.featureFullAnalysis")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("pricing.lifetimeNoPayments")}
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("pricing.lifetimePriority")}
                </li>
                <li className="flex items-center gap-2">
                  <Gem className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} />
                  <span>{t("pricing.lifetimeUnlimitedAI")}</span>
                </li>
              </ul>
              <button
                type="button"
                onClick={() => goToWhop("lifetime", "modal-lifetime")}
                disabled={currentPlan === "lifetime" || loadingPlan !== null}
                className="mt-4 w-full py-2.5 px-4 rounded-xl font-semibold text-[#0d0d12] text-sm bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 hover:shadow-[0_0_18px_5px_rgba(245,158,11,0.45)] transition-all duration-300 disabled:opacity-50 disabled:text-zinc-500 flex items-center justify-center gap-2"
              >
                {loadingPlan === "lifetime" ? (
                  <>
                    <Spinner className="w-5 h-5 flex-shrink-0 text-[#0d0d12]" />
                    <span>Redirecting...</span>
                  </>
                ) : currentPlan === "lifetime" ? (
                  t("pricing.currentPlan")
                ) : currentPlan === "starter" || currentPlan === "pro" ? (
                  `${t("pricing.upgradeLifetime")} - ${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}`
                ) : (
                  `${t("pricing.unlockLifetime")} - ${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}`
                )}
              </button>
              {loadingPlan === "lifetime" && user?.email && (
                <p className="mt-2 text-xs text-zinc-400 text-center max-w-[280px] mx-auto">
                  {t("checkout.emailNotice").replace("{email}", user.email)}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined" ? createPortal(modal, document.body) : null;
}
