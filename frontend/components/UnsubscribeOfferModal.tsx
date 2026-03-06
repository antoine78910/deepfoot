"use client";

import { useLanguage } from "@/contexts/LanguageContext";

const ACCENT = "#00ffe8";

type UnsubscribeOfferModalProps = {
  open: boolean;
  onClose: () => void;
  onEnjoyOffer: () => void;
  onConfirmCancel: () => void;
};

function GiftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 12 20 22 4 22 4 12" />
      <rect width="20" height="5" x="2" y="7" />
      <line x1="12" y1="22" x2="12" y2="7" />
      <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" />
      <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
    </svg>
  );
}

export function UnsubscribeOfferModal({
  open,
  onClose,
  onEnjoyOffer,
  onConfirmCancel,
}: UnsubscribeOfferModalProps) {
  const { t } = useLanguage();

  if (!open) return null;

  const stayOffer = t("account.stayOffer");
  const parts = stayOffer.split("-50%");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} aria-hidden />
      <div className="relative w-full max-w-md rounded-2xl bg-[#0a0a0f] border border-[#00ffe8]/30 shadow-xl shadow-[#00ffe8]/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            {t("account.waitTitle")} 🎁
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
            aria-label="Close"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex justify-center my-6">
          <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: `${ACCENT}20`, color: ACCENT }}>
            <GiftIcon className="w-8 h-8" />
          </div>
        </div>

        <p className="text-center text-white font-semibold text-lg mb-1">
          {t("account.specialOffer")}
        </p>
        <p className="text-center text-zinc-300 text-sm mb-6">
          {parts[0]}
          <span className="font-bold" style={{ color: ACCENT }}>-50%</span>
          {parts[1]}
        </p>

        <div className="rounded-xl bg-zinc-800/50 border-2 border-dashed p-4 mb-6 flex items-center justify-between gap-3" style={{ borderColor: `${ACCENT}50` }}>
          <div>
            <p className="font-bold" style={{ color: ACCENT }}>{t("account.discountLabel")}</p>
            <p className="text-sm text-zinc-400">{t("account.exclusiveOffer")}</p>
          </div>
          <span className="text-2xl">🎉</span>
        </div>

        <button
          type="button"
          onClick={onEnjoyOffer}
          className="w-full py-3.5 px-4 rounded-xl font-semibold text-[#0d0d12] transition flex items-center justify-center gap-2 hover:shadow-[0_0_20px_4px_rgba(0,255,232,0.4)]"
          style={{ backgroundColor: ACCENT }}
        >
          {t("account.enjoyOffer")} 🎁
        </button>

        <button
          type="button"
          onClick={onConfirmCancel}
          className="w-full mt-4 text-center text-sm text-zinc-500 hover:text-zinc-400 transition"
        >
          {t("account.noThanksCancel")}
        </button>
      </div>
    </div>
  );
}
