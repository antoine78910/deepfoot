"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Lock, Clock } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const ACCENT = "#00ffe8";

const BULLET_ITEMS: { key: "unlockModal1.featureProbableScore" | "unlockModal1.featureDetailedProb" | "unlockModal1.featureScenarios" | "unlockModal1.featureFullAnalysis" | "unlockModal1.featureBookmaker"; emoji: string }[] = [
  { key: "unlockModal1.featureProbableScore", emoji: "🎯" },
  { key: "unlockModal1.featureDetailedProb", emoji: "📊" },
  { key: "unlockModal1.featureScenarios", emoji: "🔮" },
  { key: "unlockModal1.featureFullAnalysis", emoji: "📝" },
  { key: "unlockModal1.featureBookmaker", emoji: "💡" },
];

const STAGGER_DELAY_MS = 200;
const ANIMATION_DURATION_MS = 450;

/** Format ISO or date string for display (e.g. "15 Mar 2025, 20:00") */
function formatMatchDate(raw: string): string {
  try {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return raw;
    return d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return raw;
  }
}

/** Countdown from now to date: "3j 8h" or "5h 30min" or "45min" */
function countdownTo(date: Date): string {
  const now = new Date();
  const ms = date.getTime() - now.getTime();
  if (ms <= 0) return "—";
  const totalMinutes = Math.floor(ms / 60000);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}j`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0 && days === 0) parts.push(`${minutes}min`);
  return parts.join(" ") || "—";
}

export function UnlockFullAnalysisModal({
  open,
  onClose,
  onUnlockClick,
  matchLabel,
  matchCountdown,
  matchDate,
}: {
  open: boolean;
  onClose: () => void;
  onUnlockClick: () => void;
  matchLabel?: string;
  /** Ex: "3j 16h" (optionnel) */
  matchCountdown?: string;
  /** Date/heure du match (ex: "15 Mar 2025, 20:00" ou chaîne brute) */
  matchDate?: string | null;
}) {
  const { t } = useLanguage();
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    if (!open) {
      setVisibleCount(0);
      return;
    }
    setVisibleCount(0);
    const delays = BULLET_ITEMS.map((_, i) =>
      setTimeout(() => setVisibleCount((c) => Math.max(c, i + 1)), (i + 1) * STAGGER_DELAY_MS)
    );
    return () => delays.forEach(clearTimeout);
  }, [open]);

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
    <div className="fixed inset-0 z-[101] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div
        className="relative w-full max-w-md rounded-2xl bg-[#1A1B22] border border-white/10 shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unlock-modal-title"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 p-2 rounded-lg text-white/90 hover:text-white hover:bg-white/10 transition z-10"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6 pt-5">
          {/* Bulle type toast — pill, pas toute la largeur */}
          <div className="flex justify-center">
            <div
              className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium"
              style={{
                background: "rgba(13, 77, 77, 0.85)",
                border: "1px solid rgba(0, 255, 232, 0.35)",
                color: "#7ee7d9",
                boxShadow: "0 0 20px -4px rgba(0, 255, 232, 0.2)",
              }}
            >
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{ color: "#7ee7d9" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <span>{t("unlockModal1.banner")}</span>
            <span className="text-base" aria-hidden>🔥</span>
            </div>
          </div>

          <h2 id="unlock-modal-title" className="text-xl sm:text-2xl font-bold text-white text-center mt-5 pr-8">
            {t("unlockModal1.title")}
          </h2>
          <p className="flex items-center justify-center gap-1.5 text-sm mt-2 text-zinc-400">
            <span aria-hidden>👥</span>
            {t("unlockModal1.socialProof")}
          </p>

          {/* What you'll unlock — styled card, smooth staggered bullets */}
          <div className="mt-6 rounded-xl p-4 sm:p-5 border border-white/5 bg-[#2C2D35]/80">
            <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-4">
              {t("unlockModal1.whatYouUnlock")}
            </p>
            <ul className="space-y-0">
              {BULLET_ITEMS.map(({ key, emoji }, index) => (
                <li
                  key={key}
                  className="flex items-center gap-3 py-2.5 text-sm text-white transition-all ease-out border-b border-white/5 last:border-0 last:pb-0"
                  style={{
                    transitionDuration: `${ANIMATION_DURATION_MS}ms`,
                    opacity: index < visibleCount ? 1 : 0,
                    transform: index < visibleCount ? "translateY(0)" : "translateY(10px)",
                  }}
                >
                  <Lock
                    className="w-4 h-4 flex-shrink-0 text-zinc-500"
                    strokeWidth={2}
                    aria-hidden
                  />
                  <span className="text-lg flex-shrink-0" aria-hidden>{emoji}</span>
                  <span className="flex-1 min-w-0">{t(key)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Match start block — "Paris SG vs Monaco starts in" puis "3j 8h" */}
          {(matchLabel || matchDate || matchCountdown) && (
            <div className="mt-4 rounded-xl px-4 py-3.5 flex items-center gap-3 bg-[#381F1A] border border-amber-500/30 shadow-[0_0_20px_-5px_rgba(245,158,11,0.2)]">
              <Clock className="w-5 h-5 flex-shrink-0 text-amber-400" strokeWidth={2} aria-hidden />
              <div className="min-w-0 flex-1">
                {matchLabel && (
                  <p className="text-white text-sm font-medium truncate">
                    {matchLabel} {t("unlockModal1.matchStartsIn")}
                  </p>
                )}
                {(matchCountdown || matchDate) && (
                  <p className="text-amber-200 font-semibold text-sm mt-1">
                    {matchCountdown ?? (matchDate ? (() => {
                      try {
                        const d = new Date(matchDate);
                        return Number.isNaN(d.getTime()) ? formatMatchDate(matchDate) : countdownTo(d);
                      } catch {
                        return formatMatchDate(matchDate);
                      }
                    })() : null)}
                  </p>
                )}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={onUnlockClick}
            className="mt-6 w-full py-3.5 px-4 rounded-xl font-semibold text-[#0d0d12] transition-all duration-300 flex items-center justify-center gap-2 bg-[#00ffe8] hover:bg-[#00ffe8]/95 hover:shadow-[0_0_18px_4px_rgba(0,255,232,0.45)]"
          >
            <span aria-hidden>🏆</span>
            {t("unlockModal1.cta")}
          </button>
          <p className="text-center text-xs mt-3 text-zinc-500">
            {t("unlockModal1.instantAccess")}
          </p>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined" ? createPortal(modal, document.body) : null;
}
