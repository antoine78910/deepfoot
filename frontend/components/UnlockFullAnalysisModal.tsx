"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Lock, Target, BarChart3, Sparkles, FileText, Lightbulb, Clock } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const ACCENT = "#00ffe8";

const BULLET_ITEMS: { key: "unlockModal1.featureProbableScore" | "unlockModal1.featureDetailedProb" | "unlockModal1.featureScenarios" | "unlockModal1.featureFullAnalysis" | "unlockModal1.featureBookmaker"; Icon: typeof Target; iconColor: string }[] = [
  { key: "unlockModal1.featureProbableScore", Icon: Target, iconColor: "text-rose-400" },
  { key: "unlockModal1.featureDetailedProb", Icon: BarChart3, iconColor: "text-[#00ffe8]" },
  { key: "unlockModal1.featureScenarios", Icon: Sparkles, iconColor: "text-violet-400" },
  { key: "unlockModal1.featureFullAnalysis", Icon: FileText, iconColor: "text-amber-400" },
  { key: "unlockModal1.featureBookmaker", Icon: Lightbulb, iconColor: "text-amber-300" },
];

const STAGGER_DELAY_MS = 90;
const ANIMATION_DURATION_MS = 450;

export function UnlockFullAnalysisModal({
  open,
  onClose,
  onUnlockClick,
  matchLabel,
  matchCountdown,
}: {
  open: boolean;
  onClose: () => void;
  onUnlockClick: () => void;
  matchLabel?: string;
  matchCountdown?: string;
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
      setTimeout(() => setVisibleCount((c) => Math.max(c, i + 1)), 80 + i * STAGGER_DELAY_MS)
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
        {/* Top banner — teal branding */}
        <div
          className="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white"
          style={{ background: `linear-gradient(135deg, ${ACCENT} 0%, #5EC2A0 100%)` }}
        >
          <span className="text-base" aria-hidden>📈</span>
          <span>{t("unlockModal1.banner")}</span>
          <span className="text-lg" aria-hidden>🔥</span>
        </div>

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
          <h2 id="unlock-modal-title" className="text-xl sm:text-2xl font-bold text-white text-center pr-8">
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
              {BULLET_ITEMS.map(({ key, Icon, iconColor }, index) => (
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
                  <span className={`w-5 h-5 flex-shrink-0 flex items-center justify-center ${iconColor}`}>
                    <Icon className="w-full h-full" strokeWidth={2} />
                  </span>
                  <span className="flex-1 min-w-0">{t(key)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Match countdown block — orange/amber style */}
          {(matchLabel || matchCountdown) && (
            <div className="mt-4 rounded-xl px-4 py-3.5 flex items-center gap-3 bg-[#381F1A] border border-amber-500/30 shadow-[0_0_20px_-5px_rgba(245,158,11,0.2)]">
              <Clock className="w-5 h-5 flex-shrink-0 text-amber-400" strokeWidth={2} aria-hidden />
              <p className="text-white text-sm font-medium">
                {matchLabel ?? "Match"}
                {matchCountdown ? (
                  <> {t("unlockModal1.matchStartsIn")} <span className="font-semibold text-amber-200">{matchCountdown}</span></>
                ) : null}
              </p>
            </div>
          )}

          <button
            type="button"
            onClick={onUnlockClick}
            className="mt-6 w-full py-3.5 px-4 rounded-xl font-semibold text-[#0d0d12] transition-all flex items-center justify-center gap-2 hover:opacity-95 hover:shadow-lg"
            style={{
              background: `linear-gradient(135deg, ${ACCENT} 0%, #5EC2A0 100%)`,
              boxShadow: `0 4px 20px -2px ${ACCENT}40`,
            }}
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
