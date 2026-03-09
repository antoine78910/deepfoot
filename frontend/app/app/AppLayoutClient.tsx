"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { BGPattern } from "@/components/BGPattern";
import { getUserFromStorage, setUserInStorage, clearAuthCookie, clearUserFromStorage, type UserInfo, type PlanId } from "@/lib/auth";
import { getDatafastVisitorId } from "@/lib/whopCheckout";
import { trackDatafastGoal } from "@/lib/datafast";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type { Lang } from "@/lib/translations";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Next midnight UTC (fallback when backend does not return next_analysis_at). */
function getNextMidnightUTC(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
}

/** Format countdown to a given ISO timestamp (next analysis at = last use + 24h). "Xh Ym" or "Xm" or "Xs". */
function formatCountdownTo(isoNextAt: string): string {
  const next = new Date(isoNextAt).getTime();
  const ms = Math.max(0, next - Date.now());
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

/** Format countdown to next midnight UTC as "Xh Ym" or "Xm" or "Xs". */
function formatCountdownToNextMidnightUTC(): string {
  const now = Date.now();
  const next = getNextMidnightUTC().getTime();
  const ms = Math.max(0, next - now);
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

const navKeys: { path: string; key: string; icon: typeof BarChartIcon; soon?: boolean }[] = [
  { path: "/matches", key: "nav.matches", icon: BarChartIcon },
  { path: "/competitions", key: "nav.competitions", icon: TrophyIcon, soon: true },
  { path: "/history", key: "nav.history", icon: HistoryIcon },
];

function BarChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}

function TrophyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </svg>
  );
}

function HistoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function CreditCardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="14" x="2" y="5" rx="2" />
      <line x1="2" y1="10" x2="22" y2="10" />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </svg>
  );
}

function SupportIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}

function LogOutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

const LANG_OPTIONS: { code: Lang; labelKey: string; flag: string }[] = [
  { code: "fr", labelKey: "lang.fr", flag: "FR" },
  { code: "en", labelKey: "lang.en", flag: "GB" },
  { code: "es", labelKey: "lang.es", flag: "ES" },
];

const PLAN_KEYS: Record<PlanId, string> = {
  free: "nav.free",
  starter: "nav.starter",
  pro: "nav.pro",
  lifetime: "nav.lifetime",
};

function PlanIcon({ plan, className }: { plan: PlanId; className?: string }) {
  const c = "w-4 h-4 flex-shrink-0";
  if (plan === "starter") {
    return (
      <svg className={className ?? c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#00ffe8" }}>
        <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
      </svg>
    );
  }
  if (plan === "pro") {
    return (
      <svg className={className ?? c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#00ffe8" }}>
        <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z" />
        <path d="M5 21h14" />
      </svg>
    );
  }
  if (plan === "lifetime") {
    return (
      <svg className={className ?? c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#f59e0b" }}>
        <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z" />
        <path d="M5 21h14" />
      </svg>
    );
  }
  return null;
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="18" x2="20" y2="18" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

export function AppLayoutClient({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, lang, setLang } = useLanguage();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [analysesUsed, setAnalysesUsed] = useState(0);
  const [analysesLimit, setAnalysesLimit] = useState<number | null>(null);
  const [nextAnalysisAt, setNextAnalysisAt] = useState<string | null>(null);
  const [nextAnalysisCountdown, setNextAnalysisCountdown] = useState<string | null>(null);
  const [langOpen, setLangOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [refreshMeTrigger, setRefreshMeTrigger] = useState(0);
  const paymentSyncAttemptedRef = useRef(false);

  useEffect(() => {
    setUser(getUserFromStorage());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onRefresh = () => setRefreshMeTrigger((n) => n + 1);
    window.addEventListener("deepfoot-refresh-me", onRefresh);
    return () => window.removeEventListener("deepfoot-refresh-me", onRefresh);
  }, []);

  // Global Whop payment sync: when returning from checkout, update plan immediately (no manual reload).
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (paymentSyncAttemptedRef.current) return;
    if (!API_URL || API_URL === "undefined") return;
    const url = new URL(window.location.href);
    const searchParams = url.searchParams;
    const paymentId = searchParams.get("payment_id") || searchParams.get("receipt_id");
    const checkoutStatus = (searchParams.get("checkout_status") || searchParams.get("status") || "").toLowerCase();
    const isSuccess = checkoutStatus === "success" || checkoutStatus === "paid";
    if (!paymentId || !isSuccess) return;

    paymentSyncAttemptedRef.current = true;
    (async () => {
      try {
        const currentUser = getUserFromStorage();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (currentUser?.id) headers["X-User-Id"] = currentUser.id;
        const res = await fetch(`${API_URL}/webhooks/whop/sync-payment`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            payment_id: paymentId,
            datafast_visitor_id: getDatafastVisitorId(),
          }),
        });
        const payload = res.ok ? await res.json().catch(() => null) : null;
        const planFromSync = payload?.plan as string | undefined;
        const validPlans: PlanId[] = ["starter", "pro", "lifetime"];
        if (planFromSync && validPlans.includes(planFromSync as PlanId)) {
          trackDatafastGoal("checkout_success", { plan: planFromSync });
          const u = getUserFromStorage();
          if (u) {
            const next: UserInfo = { ...u, plan: planFromSync as PlanId, subscription_ends_at: null };
            setUserInStorage(next);
            setUser(next);
          }
        }
      } catch {
        // ignore sync errors; user can still refresh or contact support
      } finally {
        try {
          ["receipt_id", "payment_id", "checkout_status", "status", "state_id"].forEach((k) => url.searchParams.delete(k));
          window.history.replaceState({}, "", `${url.pathname}${url.search}`);
        } catch {
          // ignore URL cleanup issues
        }
      }
    })();
  }, []);

  useEffect(() => {
    const uid = user?.id;
    if (!API_URL || API_URL === "undefined") return;
    const ac = new AbortController();
    const headers: Record<string, string> = {};
    if (uid) headers["X-User-Id"] = uid;
    (async () => {
      try {
        const r = await fetch(`${API_URL}/me`, { headers, signal: ac.signal });
        const data = r.ok ? (await r.json()) : null;
        if (data && typeof data === "object") {
          setAnalysesUsed(Number(data.analyses_used_today) || 0);
          setAnalysesLimit(data.analyses_limit !== undefined ? data.analyses_limit : null);
          setNextAnalysisAt((data as { next_analysis_at?: string | null }).next_analysis_at ?? null);
          let planToSet = data.plan as PlanId | undefined;
          if (data.plan === "free" && uid) {
            try {
              const syncRes = await fetch(`${API_URL}/me/sync-plan`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-User-Id": uid },
                signal: ac.signal,
              });
              const syncData = syncRes.ok ? (await syncRes.json()) : null;
              if (syncData && typeof syncData === "object" && syncData.updated && syncData.plan) {
                planToSet = syncData.plan as PlanId;
              }
            } catch {
              // ignore sync-plan errors
            }
          }
          if (uid) {
            const u = getUserFromStorage();
            const newPlan = (planToSet ?? u?.plan ?? "free") as PlanId;
            const endsAt = (data as { subscription_ends_at?: string | null }).subscription_ends_at ?? u?.subscription_ends_at;
            if (u && (u.plan !== newPlan || u.id !== uid || (u.subscription_ends_at ?? null) !== (endsAt ?? null))) {
              setUserInStorage({ ...u, id: uid, plan: newPlan, subscription_ends_at: endsAt ?? undefined });
              setUser({ ...u, id: uid, plan: newPlan, subscription_ends_at: endsAt ?? undefined });
            }
          }
        }
      } catch {
        // Ignore: network error, abort, or invalid JSON
      }
    })();
    return () => ac.abort();
    // Refetch on route change or when analyze page signals consumption (e.g. view from history)
  }, [user?.id, pathname, refreshMeTrigger]);

  // Countdown to next analysis: 24h from last use when limit reached (unique per user/session)
  useEffect(() => {
    const plan = user?.plan ?? "free";
    const limit = plan === "starter" ? 1 : analysesLimit;
    const isAtLimit = limit != null && analysesUsed >= limit;
    if (!isAtLimit) {
      setNextAnalysisCountdown(null);
      return;
    }
    const tick = () => {
      if (nextAnalysisAt) {
        const countdown = formatCountdownTo(nextAnalysisAt);
        setNextAnalysisCountdown(countdown);
      } else {
        setNextAnalysisCountdown(formatCountdownToNextMidnightUTC());
      }
    };
    tick();
    const interval = setInterval(tick, 60_000);
    return () => clearInterval(interval);
  }, [user?.plan, analysesUsed, analysesLimit, nextAnalysisAt]);

  const handleSignOut = async () => {
    try {
      const supabase = getSupabaseBrowserClient();
      await supabase.auth.signOut();
    } catch {
      // ignore
    }
    clearAuthCookie();
    clearUserFromStorage();
    router.push("/");
  };

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="min-h-screen bg-app-gradient text-zinc-200 flex flex-col md:flex-row relative">
      <BGPattern variant="grid" mask="fade-edges" size={24} fill="rgba(0,255,232,0.07)" className="fixed inset-0" />
      {/* Mobile header: logo + hamburger */}
      <header className="md:hidden flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-white/10 bg-[#0a0a0e]/50 backdrop-blur-md sticky top-0 z-30">
        <Link href="/" className="flex items-center">
          <img src="/logo.png" alt="DEEPFOOT" className="h-12 w-auto object-contain" />
        </Link>
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition"
          aria-label="Open menu"
        >
          <MenuIcon className="w-6 h-6" />
        </button>
      </header>

      {/* Sidebar: overlay on mobile, static on md+ */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          aria-hidden
          onClick={closeSidebar}
        />
      )}
      <aside
        className={`
          w-64 flex-shrink-0 flex flex-col
          fixed md:static inset-y-0 left-0 z-50 md:z-auto
          h-full md:h-screen
          transform transition-transform duration-200 ease-out
          md:translate-x-0 md:sticky md:top-0
          overflow-y-auto border-r border-dark-border bg-dark-card/50
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        <div className="px-5 pt-4 pb-3 flex items-center justify-between md:justify-center">
          <Link href="/" className="flex items-center justify-center" onClick={closeSidebar}>
            <img
              src="/logo.png"
              alt="DEEPFOOT"
              className="h-14 w-auto object-contain max-w-full"
            />
          </Link>
          <button
            type="button"
            onClick={closeSidebar}
            className="md:hidden p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10"
            aria-label="Close menu"
          >
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <nav className="px-4 flex-1">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider px-3 mb-2">Analysis</p>
          <ul className="space-y-0.5">
            {navKeys.map(({ path, key, icon: Icon, soon }) => {
              const href = path === "/" ? "/" : path;
              const label = t(key);
              const active =
                !soon &&
                (pathname === href || pathname === `/app${path}` || (path !== "/" && (pathname?.startsWith(href) || pathname?.startsWith(`/app${path}`))));
              if (soon) {
                return (
                  <li key={path}>
                    <span
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-zinc-500 cursor-not-allowed border border-transparent"
                      aria-disabled
                    >
                      <Icon className="flex-shrink-0 opacity-60" />
                      <span className="flex-1">{label}</span>
                      <span className="text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-400">
                        {t("nav.soon")}
                      </span>
                    </span>
                  </li>
                );
              }
              return (
                <li key={path}>
                  <Link
                    href={href}
                    onClick={closeSidebar}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                      active
                        ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8] shadow-[0_0_10px_2px_rgba(0,255,232,0.2)]"
                        : "border border-transparent text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                    }`}
                  >
                    <Icon className="flex-shrink-0" />
                    {label}
                  </Link>
                </li>
              );
            })}
            <li>
              <Link
                href="/pricing"
                onClick={closeSidebar}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm border transition-all duration-200 ${
                  pathname === "/pricing" || pathname === "/app/pricing" || pathname?.startsWith("/app/pricing")
                    ? "border-amber-500/70 bg-amber-500/15 text-amber-400 shadow-[0_0_10px_2px_rgba(245,158,11,0.2)]"
                    : "border-amber-500/50 bg-[#15171c]/80 text-zinc-200 hover:bg-zinc-800/50 hover:border-amber-500/70"
                }`}
              >
                <CreditCardIcon className="flex-shrink-0" />
                <span className="flex-1">{t("nav.pricing")}</span>
                <span className="text-xs font-medium uppercase tracking-wider px-2 py-1 rounded-md bg-amber-900/70 text-amber-200">
                  {t("nav.upgrade")}
                </span>
              </Link>
            </li>
          </ul>

          <div className="mt-6 px-3">
            <p className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
              <BarChartIcon className="w-4 h-4" />
              {t("nav.todayAnalyses")}
            </p>
            {(() => {
              const plan = user?.plan ?? "free";
              const effectiveLimit = plan === "starter" ? 1 : analysesLimit;
              const limitNum = effectiveLimit != null ? effectiveLimit : (plan === "free" ? 0 : null);
              const isOverLimit = plan === "free" ? true : (effectiveLimit != null && analysesUsed >= effectiveLimit);
              const displayLimit = plan === "free" ? "0" : (effectiveLimit == null ? "∞" : String(effectiveLimit));
              return (
                <>
                  <p className={`text-lg font-bold ${isOverLimit ? "text-red-400" : "text-white"}`}>
                    {plan === "free" ? "0/0" : `${analysesUsed}/${displayLimit}`}
                  </p>
                  <div className="h-1.5 bg-zinc-800 rounded-full mt-1 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${isOverLimit ? "bg-red-500" : "bg-accent-green"}`}
                      style={{ width: `${plan === "free" ? 100 : limitNum != null && limitNum > 0 ? Math.min(100, (analysesUsed / limitNum) * 100) : 0}%` }}
                    />
                  </div>
                </>
              );
            })()}
            {(() => {
              const plan = user?.plan ?? "free";
              const effectiveLimit = plan === "starter" ? 1 : analysesLimit;
              const isLimitReached = plan === "free" || (effectiveLimit != null && analysesUsed >= effectiveLimit);
              return isLimitReached ? (
                <div className="text-xs text-zinc-400 mt-2 space-y-0.5">
                  {nextAnalysisCountdown && (
                    <p className="text-[#00ffe8]/90">
                      {t("nav.nextAnalysisIn").replace("{time}", nextAnalysisCountdown)}
                    </p>
                  )}
                  <p>
                    {t("nav.limitReached")} •{" "}
                    <Link href="/pricing" className="text-[#00ffe8] hover:underline">
                      {t("nav.upgradeForMore")}
                    </Link>
                  </p>
                </div>
              ) : null;
            })()}
          </div>
        </nav>

        <div className="p-4 pt-6 mt-4 border-t border-dark-border flex flex-col flex-1 min-h-0">
          <div className="mt-auto space-y-1">
            <Link
              href="/account"
              onClick={closeSidebar}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
                pathname === "/account" || pathname === "/app/account" || pathname?.startsWith("/app/account")
                  ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8] shadow-[0_0_10px_2px_rgba(0,255,232,0.2)]"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 border border-transparent"
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center flex-shrink-0">
                <UserIcon className="w-4 h-4 text-zinc-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white truncate">
                  {user?.displayName ?? user?.email ?? "—"}
                </p>
                <p className="text-xs text-zinc-500 flex items-center gap-1 mt-0.5">
                  {user?.plan && user.plan !== "free" ? (
                    <>
                      <PlanIcon plan={user.plan} className="w-3 h-3 flex-shrink-0" />
                      {t(PLAN_KEYS[user.plan])}
                    </>
                  ) : (
                    t("nav.free")
                  )}
                </p>
              </div>
            </Link>
            <button
              type="button"
              onClick={handleSignOut}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 text-left"
            >
              <LogOutIcon className="flex-shrink-0" />
              {t("nav.signOut")}
            </button>
            <a
              href="mailto:app@deepfoot.io"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
            >
              <SupportIcon className="flex-shrink-0" />
              {t("nav.support")}
            </a>
            <div className="relative pt-2">
            <button
              type="button"
              onClick={() => setLangOpen((o) => !o)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm border text-left transition-all duration-200 ${
                langOpen
                  ? "bg-[#00ffe8]/15 border-[#00ffe8]/70 text-[#00ffe8] shadow-[0_0_10px_2px_rgba(0,255,232,0.2)]"
                  : "border-transparent text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
              }`}
            >
              <GlobeIcon className="flex-shrink-0" />
              <span className="flex-1">
                {LANG_OPTIONS.find((o) => o.code === lang)?.flag ?? "GB"} {t(`lang.${lang}`)}
              </span>
            </button>
            {langOpen && (
              <>
                <div
                  className="absolute left-0 right-0 bottom-full z-20 mb-0.5 rounded-xl bg-[#1c1c28] border border-white/10 shadow-xl overflow-hidden animate-lang-dropdown py-1"
                  style={{ transformOrigin: "bottom" }}
                >
                  {LANG_OPTIONS.map((opt) => (
                    <button
                      key={opt.code}
                      type="button"
                      onClick={() => {
                        setLang(opt.code);
                        setLangOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left rounded-lg border transition-all duration-200 ${
                        opt.code === lang
                          ? "bg-[#00ffe8]/15 border-[#00ffe8]/70 text-[#00ffe8] shadow-[0_0_10px_2px_rgba(0,255,232,0.2)] mx-1"
                          : "border-transparent text-zinc-300 hover:bg-zinc-800/50 hover:text-zinc-200 hover:border-zinc-600/50 mx-1"
                      }`}
                    >
                      {opt.flag} {t(opt.labelKey)}
                    </button>
                  ))}
                </div>
                <div className="fixed inset-0 z-10" aria-hidden onClick={() => setLangOpen(false)} />
              </>
            )}
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto min-w-0 px-2 md:px-0 py-4 md:py-0">
        {children}
      </main>
    </div>
  );
}
