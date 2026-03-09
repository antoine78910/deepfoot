"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { getUserFromStorage, setUserInStorage, type PlanId } from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { useGeoCurrency } from "@/hooks/useGeoCurrency";
import { formatPrice } from "@/lib/geoCurrency";
import { UnsubscribeOfferModal } from "@/components/UnsubscribeOfferModal";
import { getWhopCheckoutUrl, getDatafastVisitorId } from "@/lib/whopCheckout";
import { Check } from "lucide-react";

function PersonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </svg>
  );
}

function WalletIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect width="20" height="14" x="2" y="5" rx="2" />
      <line x1="2" y1="10" x2="22" y2="10" />
      <path d="M16 14h.01" />
    </svg>
  );
}

function SupportQuestionIcon({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center justify-center w-5 h-5 text-lg font-bold ${className ?? ""}`} aria-hidden>?</span>
  );
}

function MailIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
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

const PLAN_KEYS: Record<string, string> = {
  free: "nav.free",
  starter: "nav.starter",
  pro: "nav.pro",
  lifetime: "nav.lifetime",
};

function formatSubscriptionEndDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, { dateStyle: "long" });
  } catch {
    return iso;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function AccountPage() {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useLanguage();
  const { config: currencyConfig, isLoading: currencyLoading } = useGeoCurrency();
  const [user, setUser] = useState<ReturnType<typeof getUserFromStorage>>(null);
  const [confirmUnsubscribeOpen, setConfirmUnsubscribeOpen] = useState(false);
  const [unsubscribeModalOpen, setUnsubscribeModalOpen] = useState(false);
  const [cancelWhopMessageOpen, setCancelWhopMessageOpen] = useState(false);
  const [cancelWhopEndDate, setCancelWhopEndDate] = useState<string | null>(null);
  const [renewSuccessOpen, setRenewSuccessOpen] = useState(false);
  const [renewLoading, setRenewLoading] = useState(false);
  const [unsubscribeSuccessMessage, setUnsubscribeSuccessMessage] = useState<string | null>(null);
  const [offerClaimedOpen, setOfferClaimedOpen] = useState(false);
  const [subscribedSince, setSubscribedSince] = useState<string>("—");
  const [editingEmail, setEditingEmail] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailMessage, setEmailMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

  useEffect(() => {
    setUser(getUserFromStorage());
  }, []);

  // Refetch /me every time we visit the account page so status (renewing vs cancelled) is always up to date
  const isAccountPage = pathname === "/account" || pathname === "/app/account" || (pathname ?? "").startsWith("/app/account");
  useEffect(() => {
    if (!isAccountPage) return;
    const u = getUserFromStorage();
    const uid = u?.id;
    if (!uid || !API_URL || API_URL === "undefined") return;
    const ac = new AbortController();
    fetch(`${API_URL}/me`, { headers: { "X-User-Id": uid }, signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && typeof data === "object") {
          const current = getUserFromStorage();
          if (current && current.id === uid) {
            const plan = (data.plan as PlanId) ?? current.plan;
            const endsAt = data.subscription_ends_at ?? current.subscription_ends_at;
            const next = { ...current, plan, subscription_ends_at: endsAt ?? undefined };
            setUserInStorage(next);
            setUser(next);
          }
          const startedAt = (data as { subscription_started_at?: string | null }).subscription_started_at;
          if (typeof startedAt === "string" && startedAt.trim()) {
            try {
              const d = new Date(startedAt.trim());
              if (!Number.isNaN(d.getTime())) {
                setSubscribedSince(d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" }));
              }
            } catch {
              setSubscribedSince("—");
            }
          } else {
            setSubscribedSince("—");
          }
        }
      })
      .catch(() => {});
    return () => ac.abort();
  }, [isAccountPage, pathname]);

  const startEditEmail = () => {
    setEditingEmail(true);
    setNewEmail(user?.email ?? "");
    setEmailMessage(null);
  };

  const cancelEditEmail = () => {
    setEditingEmail(false);
    setNewEmail("");
    setEmailMessage(null);
  };

  const saveEmail = async () => {
    const trimmed = newEmail.trim();
    if (!trimmed || trimmed === user?.email) {
      cancelEditEmail();
      return;
    }
    setEmailLoading(true);
    setEmailMessage(null);
    try {
      const supabase = getSupabaseBrowserClient();
      const { error } = await supabase.auth.updateUser({ email: trimmed });
      if (error) throw error;
      setEmailMessage({ type: "success", text: t("account.emailConfirmSent") });
      setEditingEmail(false);
      setNewEmail("");
    } catch {
      setEmailMessage({ type: "error", text: t("account.emailChangeError") });
    } finally {
      setEmailLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      const supabase = getSupabaseBrowserClient();
      await supabase.auth.signOut();
    } catch {
      // ignore
    }
    if (typeof window !== "undefined") {
      document.cookie = "visifoot_session=; path=/; max-age=0";
      localStorage.removeItem("visifoot_logged_in");
      localStorage.removeItem("visifoot_user");
      router.push("/");
    }
  };

  const handleEnjoyOffer = async () => {
    setUnsubscribeModalOpen(false);
    if (user?.id && API_URL && API_URL !== "undefined") {
      try {
        await fetch(`${API_URL}/me/notify-offer-claim`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-User-Id": user.id },
        });
      } catch {
        // ignore: popup shown anyway
      }
    }
    setOfferClaimedOpen(true);
  };

  const handleConfirmCancel = async () => {
    if (!user?.id || !API_URL || API_URL === "undefined") {
      setUnsubscribeModalOpen(false);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/me/cancel-subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Id": user.id },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err?.detail ?? "Could not cancel subscription. Try from your Whop account.");
        return;
      }
      const data = await res.json().catch(() => ({}));
      const newPlan = (data?.plan && typeof data.plan === "string") ? data.plan : user?.plan ?? "free";
      const endsAt = typeof data?.subscription_ends_at === "string" ? data.subscription_ends_at : undefined;
      const u = getUserFromStorage();
      if (u && u.id === user.id) {
        const next = { ...u, plan: newPlan as PlanId, subscription_ends_at: endsAt ?? u.subscription_ends_at };
        setUserInStorage(next);
        setUser(next);
      }
      setUnsubscribeModalOpen(false);
      if (data?.cancelled_via_whop === true) {
        const endDate = endsAt ? formatSubscriptionEndDate(endsAt) : null;
        const msg = endDate
          ? t("account.subscriptionEndsOnFromWhop").replace("{date}", endDate)
          : t("account.unsubscribedSuccess");
        setUnsubscribeSuccessMessage(msg);
      } else {
        setCancelWhopEndDate(endsAt ?? null);
        setCancelWhopMessageOpen(true);
      }
    } catch {
      alert("Network error. Try again later.");
    }
  };

  const handleRenewPlan = async () => {
    if (!user?.id || !API_URL || API_URL === "undefined") return;
    setRenewLoading(true);
    try {
      const res = await fetch(`${API_URL}/me/renew-subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Id": user.id },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err?.detail ?? "Could not renew. Try again or contact support.");
        return;
      }
      const data = await res.json().catch(() => ({}));
      const u = getUserFromStorage();
      if (u && u.id === user.id) {
        const next = { ...u, subscription_ends_at: undefined };
        setUserInStorage(next);
        setUser(next);
      }
      setRenewSuccessOpen(true);
    } catch {
      alert("Network error. Try again later.");
    } finally {
      setRenewLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white">{t("account.title")}</h1>
      <p className="text-zinc-500 mt-1">{t("account.subtitle")}</p>

      {unsubscribeSuccessMessage && (
        <div className="mt-6 rounded-xl bg-emerald-500/20 border border-emerald-500/50 px-4 py-3 text-emerald-200 flex items-center justify-between gap-3">
          <span>{unsubscribeSuccessMessage}</span>
          <button
            type="button"
            onClick={() => setUnsubscribeSuccessMessage(null)}
            className="p-1 rounded-lg text-emerald-300 hover:text-white hover:bg-emerald-500/30 transition"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Personal information */}
      <div className="mt-8 rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
          <PersonIcon className="text-zinc-400 flex-shrink-0" />
          {t("account.personalInfo")}
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-zinc-500 mb-1">{t("account.emailAddress")}</label>
            {editingEmail ? (
              <div className="space-y-2">
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full rounded-xl bg-dark-input border border-dark-border px-4 py-3 text-white"
                  placeholder={user?.email ?? ""}
                  disabled={emailLoading}
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={saveEmail}
                    disabled={emailLoading || !newEmail.trim() || newEmail.trim() === user?.email}
                    className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition disabled:opacity-50"
                  >
                    {emailLoading ? "…" : t("account.save")}
                  </button>
                  <button
                    type="button"
                    onClick={cancelEditEmail}
                    disabled={emailLoading}
                    className="px-4 py-2.5 rounded-xl bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium transition disabled:opacity-50"
                  >
                    {t("account.cancel")}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="email"
                  readOnly
                  value={user?.email ?? ""}
                  className="flex-1 rounded-xl bg-dark-input border border-dark-border px-4 py-3 text-white read-only:opacity-90"
                />
                <button
                  type="button"
                  onClick={startEditEmail}
                  className="px-4 py-3 rounded-xl bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium transition"
                >
                  {t("account.edit")}
                </button>
              </div>
            )}
            {emailMessage && (
              <p className={`mt-2 text-sm ${emailMessage.type === "success" ? "text-emerald-400" : "text-red-400"}`}>
                {emailMessage.text}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm text-zinc-500 mb-1">{t("account.subscribedSince")}</label>
            <div className="rounded-xl bg-dark-input border border-dark-border px-4 py-3 text-white">
              {subscribedSince}
            </div>
          </div>
        </div>
      </div>

      {/* Subscription */}
      <div className="mt-6 rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
          <WalletIcon className="text-zinc-400 flex-shrink-0" />
          {t("account.subscription")}
        </h2>
        <div className="mb-4">
          <p className="text-sm text-zinc-500">{t("account.currentPlan")}</p>
          <p className="text-lg font-bold text-white mt-0.5 flex items-center gap-2">
            {user?.plan && user.plan !== "free" ? (
              <>
                {user.plan === "starter" && (
                  <span className="w-5 h-5 flex-shrink-0" style={{ color: "#00ffe8" }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
                    </svg>
                  </span>
                )}
                {user.plan === "pro" && (
                  <span className="w-5 h-5 flex-shrink-0" style={{ color: "#00ffe8" }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
                      <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z" />
                      <path d="M5 21h14" />
                    </svg>
                  </span>
                )}
                {user.plan === "lifetime" && (
                  <span className="w-5 h-5 flex-shrink-0 text-amber-400">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
                      <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z" />
                      <path d="M5 21h14" />
                    </svg>
                  </span>
                )}
                {t(PLAN_KEYS[user.plan])}
              </>
            ) : (
              t("nav.free")
            )}
          </p>
        </div>
        <div className="mb-6">
          <p className="text-sm text-zinc-500">{t("account.status")}</p>
          <p className={`flex items-center gap-2 mt-0.5 ${user?.subscription_ends_at ? "text-white" : "text-emerald-400"}`}>
            {!user?.subscription_ends_at && <Check className="w-4 h-4 flex-shrink-0" strokeWidth={2.5} />}
            {user?.subscription_ends_at
              ? t("account.planCancelledEndsOn").replace("{date}", formatSubscriptionEndDate(user.subscription_ends_at))
              : t("account.active")}
          </p>
        </div>

        {/* Go Lifetime card - same branding as pricing */}
        <div className="relative rounded-2xl bg-[#14141c]/70 border-2 border-amber-500/60 p-5 mb-6 backdrop-blur-sm shadow-[0_0_30px_-5px_rgba(245,158,11,0.2)] hover:shadow-[0_0_45px_-5px_rgba(245,158,11,0.35)] transition-all duration-300">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-6 h-6 flex-shrink-0 text-amber-400">
              <InfinityIcon className="w-full h-full" />
            </span>
            <h3 className="text-lg font-bold text-white">{t("account.goLifetime")}</h3>
          </div>
          <p className="text-zinc-400 text-sm mt-0.5">{t("account.lifetimeAccess")}</p>
          <ul className="mt-3 space-y-1.5 text-sm text-zinc-300">
            <li className="flex items-center gap-2">
              <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("account.noMonthlyPayments")}
            </li>
            <li className="flex items-center gap-2">
              <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("account.unlimitedAnalyses")}
            </li>
            <li className="flex items-center gap-2">
              <Check className="w-4 h-4 flex-shrink-0 text-amber-400" strokeWidth={2.5} /> {t("account.allPremiumFeatures")}
            </li>
          </ul>
          <p className="text-xl font-bold text-amber-400 mt-4">
            ⚡ {currencyLoading ? "—" : `${formatPrice(currencyConfig, currencyConfig.lifetimeAmount)}${currencyConfig.lifetimeSuffix}`}
          </p>
          <button
            type="button"
            onClick={() => {
              window.location.href = getWhopCheckoutUrl("lifetime", currencyConfig.currency, getDatafastVisitorId(), "account-lifetime", user?.email, user?.whop_membership_id);
            }}
            className="mt-4 w-full py-3 px-4 rounded-xl font-semibold text-[#0d0d12] bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 hover:shadow-[0_0_22px_6px_rgba(245,158,11,0.45)] transition-all duration-300 shadow-[0_0_20px_-5px_rgba(245,158,11,0.4)]"
          >
            {t("account.upgradeToLifetime")}
          </button>
          {user?.email && (
            <p className="mt-2 text-xs text-zinc-400 text-center">
              {t("checkout.emailNotice").replace("{email}", user.email)}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-3 mt-3">
          <Link
            href="/pricing"
            className="px-4 py-2.5 rounded-xl bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium transition"
          >
            {t("account.seeAllPlans")}
          </Link>
          {user?.plan && user.plan !== "free" && (
            user?.subscription_ends_at ? (
              <button
                type="button"
                disabled={renewLoading}
                onClick={handleRenewPlan}
                className="px-4 py-2.5 rounded-xl bg-[#00ffe8]/15 border border-[#00ffe8]/50 text-[#00ffe8] hover:bg-[#00ffe8]/25 hover:border-[#00ffe8] disabled:opacity-60 text-sm font-medium transition"
              >
                {renewLoading ? "…" : t("account.renewPlan")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setUnsubscribeSuccessMessage(null);
                  setConfirmUnsubscribeOpen(true);
                }}
                className="px-4 py-2.5 rounded-xl bg-zinc-700 hover:bg-zinc-600 text-red-400 hover:text-red-300 text-sm font-medium transition"
              >
                {t("account.unsubscribe")}
              </button>
            )
          )}
        </div>
      </div>

      {/* Support */}
      <div className="mt-6 rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-2">
          <SupportQuestionIcon className="text-[#00ffe8] flex-shrink-0" />
          {t("account.support")}
        </h2>
        <p className="text-zinc-500 text-sm mb-4">{t("account.supportDesc")}</p>
        <a
          href="mailto:support@deepfoot.io"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#00ffe8]/60 text-[#00ffe8] hover:bg-[#00ffe8]/10 text-sm font-medium transition"
        >
          <MailIcon />
          {t("account.contactSupport")}
        </a>
      </div>

      {/* Modal: Are you sure you want to unsubscribe? (style comme offre -50%) */}
      {confirmUnsubscribeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setConfirmUnsubscribeOpen(false)} aria-hidden />
          <div className="relative w-full max-w-md rounded-2xl bg-[#0a0a0f] border border-[#00ffe8]/30 shadow-xl shadow-[#00ffe8]/10 p-6">
            <h2 className="text-xl font-bold text-white mb-2">{t("account.unsubscribeConfirmTitle")}</h2>
            <p className="text-zinc-300 text-sm mb-6">{t("account.unsubscribeConfirmMessage")}</p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setConfirmUnsubscribeOpen(false)}
                className="flex-1 py-2.5 px-4 rounded-xl font-semibold text-zinc-300 bg-zinc-700 hover:bg-zinc-600 transition"
              >
                {t("account.cancel")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmUnsubscribeOpen(false);
                  setUnsubscribeModalOpen(true);
                }}
                className="flex-1 py-2.5 px-4 rounded-xl font-semibold text-white bg-red-600 hover:bg-red-500 transition"
              >
                {t("account.unsubscribeConfirmYes")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: subscription ends on [date] from Whop or cancelled */}
      {cancelWhopMessageOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => { setCancelWhopMessageOpen(false); setCancelWhopEndDate(null); }} aria-hidden />
          <div className="relative w-full max-w-md rounded-2xl bg-[#0a0a0f] border border-amber-500/30 shadow-xl p-6">
            <h2 className="text-xl font-bold text-white mb-2">{t("account.planSetFreeTitle")}</h2>
            <p className="text-zinc-300 text-sm mb-6">
              {cancelWhopEndDate
                ? t("account.subscriptionEndsOnFromWhop").replace("{date}", formatSubscriptionEndDate(cancelWhopEndDate))
                : t("account.subscriptionCancelled")}
            </p>
            <button
              type="button"
              onClick={() => { setCancelWhopMessageOpen(false); setCancelWhopEndDate(null); }}
              className="w-full py-2.5 px-4 rounded-xl font-semibold text-[#0d0d12] bg-[#00ffe8] hover:opacity-90 transition"
            >
              {t("account.close")}
            </button>
          </div>
        </div>
      )}

      {/* Modal: You just renewed your plan */}
      {renewSuccessOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setRenewSuccessOpen(false)} aria-hidden />
          <div className="relative w-full max-w-md rounded-2xl bg-[#0a0a0f] border border-[#00ffe8]/30 shadow-xl shadow-[#00ffe8]/10 p-6">
            <h2 className="text-xl font-bold text-white mb-2">{t("account.renewSuccess")}</h2>
            <p className="text-zinc-300 text-sm mb-6">{t("account.active")}</p>
            <button
              type="button"
              onClick={() => setRenewSuccessOpen(false)}
              className="w-full py-2.5 px-4 rounded-xl font-semibold text-[#0d0d12] bg-[#00ffe8] hover:opacity-90 transition"
            >
              {t("account.close")}
            </button>
          </div>
        </div>
      )}

      {/* Popup validation : offre -50% enregistrée + email envoyé à anto.delbos@gmail.com si RESEND_API_KEY */}
      {offerClaimedOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setOfferClaimedOpen(false)} aria-hidden />
          <div className="relative w-full max-w-sm rounded-2xl bg-[#0a0a0f] border border-[#00ffe8]/30 shadow-xl p-6 text-center">
            <h2 className="text-lg font-bold text-white mb-2">{t("account.offerClaimedTitle")}</h2>
            <p className="text-zinc-300 text-sm mb-6">{t("account.offerClaimedMessage")}</p>
            <button
              type="button"
              onClick={() => setOfferClaimedOpen(false)}
              className="w-full py-2.5 px-4 rounded-xl font-semibold text-[#0d0d12] bg-[#00ffe8] hover:opacity-90 transition"
            >
              {t("account.close")}
            </button>
          </div>
        </div>
      )}

      <UnsubscribeOfferModal
        open={unsubscribeModalOpen}
        onClose={() => setUnsubscribeModalOpen(false)}
        onEnjoyOffer={handleEnjoyOffer}
        onConfirmCancel={handleConfirmCancel}
      />
    </div>
  );
}
