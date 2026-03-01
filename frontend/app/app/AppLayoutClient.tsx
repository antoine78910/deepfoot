"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";
import { getUserFromStorage, clearAuthCookie, clearUserFromStorage, type UserInfo, type PlanId } from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

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

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
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

const PLAN_KEYS: Record<PlanId, string> = {
  free: "nav.free",
  starter: "nav.starter",
  pro: "nav.pro",
  lifetime: "nav.lifetime",
};

export function AppLayoutClient({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const basePath = useAppBasePath();
  const [user, setUser] = useState<UserInfo | null>(null);
  const analysesUsed = 0;
  const analysesLimit = 1;

  useEffect(() => {
    setUser(getUserFromStorage());
  }, []);

  const handleSignOut = async () => {
    try {
      const supabase = getSupabaseBrowserClient();
      await supabase.auth.signOut();
    } catch {
      // ignore
    }
    clearAuthCookie();
    clearUserFromStorage();
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-app-gradient text-zinc-200 flex">
      <aside className="w-64 flex-shrink-0 sticky top-0 h-screen overflow-y-auto border-r border-dark-border bg-dark-card/50 flex flex-col">
        <div className="px-5 pt-4 pb-3 flex justify-center">
          <Link href={basePath || "/"} className="flex items-center justify-center">
            <img
              src="/logo.png"
              alt="DEEPFOOT"
              className="h-14 w-auto object-contain max-w-full"
            />
          </Link>
        </div>

        <nav className="px-4 flex-1">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider px-3 mb-2">Analysis</p>
          <ul className="space-y-0.5">
            {navKeys.map(({ path, key, icon: Icon, soon }) => {
              const href = `${basePath}${path}`;
              const internalPath = `/app${path}`;
              const label = t(key);
              const active =
                !soon &&
                (pathname === href ||
                  pathname === internalPath ||
                  (path !== "/" && pathname?.startsWith(href)) ||
                  (path !== "/" && pathname?.startsWith(internalPath)));
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
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      active
                        ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8]"
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
                href={`${basePath}/pricing`}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm border border-amber-500/50 bg-[#15171c]/80 text-zinc-200 hover:bg-zinc-800/50 hover:border-amber-500/70 transition-colors"
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
            <p className="text-lg font-bold text-white">{analysesUsed}/{analysesLimit}</p>
            <div className="h-1.5 bg-zinc-800 rounded-full mt-1 overflow-hidden">
              <div
                className="h-full bg-accent-green rounded-full transition-all"
                style={{ width: `${(analysesUsed / analysesLimit) * 100}%` }}
              />
            </div>
          </div>
        </nav>

        <div className="p-4 border-t border-dark-border">
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center">
              <UserIcon className="w-4 h-4 text-zinc-400" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.displayName ?? user?.email ?? "—"}
              </p>
              <p className="text-xs text-zinc-500">
                {user?.plan ? t(PLAN_KEYS[user.plan]) : t("nav.free")}
              </p>
            </div>
          </div>
          <Link
            href={`${basePath}/account`}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
              pathname === `${basePath}/account` || pathname === "/app/account"
                ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8]"
                : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
            }`}
          >
            <UserIcon className="flex-shrink-0" />
            {t("nav.account")}
          </Link>
          <Link
            href={`${basePath}/settings`}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
          >
            <SettingsIcon className="flex-shrink-0" />
            {t("nav.settings")}
          </Link>
          <Link
            href={`${basePath}/support`}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
          >
            <SupportIcon className="flex-shrink-0" />
            {t("nav.support")}
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 text-left"
          >
            <LogOutIcon className="flex-shrink-0" />
            {t("nav.signOut")}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
