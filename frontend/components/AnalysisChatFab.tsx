"use client";

import { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { MessageCircle, Lock, Crown, X, Send } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { getUserFromStorage, setUserInStorage, type PlanId } from "@/lib/auth";
import { getApiUrl } from "@/lib/api";
import { UnlockPricingModal, type PricingModalVariant } from "./UnlockPricingModal";

const ACCENT = "#00ffe8";

type ChatMessage = { role: "user" | "assistant"; content: string };

function remainingFromPlan(plan: string): number | null {
  if (plan === "lifetime") return null;
  if (plan === "pro") return 1;
  return 0;
}

export function AnalysisChatFab({
  analysisData,
  matchLabel,
}: {
  analysisData: Record<string, unknown>;
  matchLabel: string;
}) {
  const { t, lang } = useLanguage();
  const user = getUserFromStorage();
  const [plan, setPlan] = useState<string>(user?.plan ?? "free");
  const canUseChat = plan === "pro" || plan === "lifetime";

  const [openChatPanel, setOpenChatPanel] = useState(false);
  const [openLockedModal, setOpenLockedModal] = useState(false);
  const [openPricingModal, setOpenPricingModal] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatRemaining, setChatRemaining] = useState<number | null>(remainingFromPlan(user?.plan ?? "free"));
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const uid = user?.id;
    if (!uid) return;
    const ac = new AbortController();
    fetch(`${getApiUrl()}/me`, { headers: { "X-User-Id": uid }, signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data || typeof data !== "object") return;
        const nextPlan = typeof data.plan === "string" ? data.plan : user?.plan ?? "free";
        setPlan(nextPlan);
        if (data.chat_remaining !== undefined) {
          setChatRemaining(data.chat_remaining === null ? null : Number(data.chat_remaining));
        } else {
          setChatRemaining(remainingFromPlan(nextPlan));
        }
        const stored = getUserFromStorage();
        if (stored && stored.plan !== nextPlan) {
          setUserInStorage({ ...stored, plan: nextPlan as PlanId });
        }
      })
      .catch(() => {});
    return () => ac.abort();
  }, [user?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleFabClick = () => {
    if (canUseChat) {
      setOpenChatPanel(true);
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setOpenLockedModal(true);
    }
  };

  const handleUnlockClick = () => {
    setOpenLockedModal(false);
    setOpenPricingModal(true);
  };

  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || loading || (plan === "pro" && chatRemaining !== null && chatRemaining <= 0)) return;
    if (!user?.id) return;

    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${getApiUrl()}/predict/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Id": user.id },
        body: JSON.stringify({
          message: text,
          analysis_context: analysisData,
          language: lang,
        }),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 403) {
        setError(data.detail || t("chat.limitReached"));
        setChatRemaining(0);
        setMessages((prev) => prev.slice(0, -1));
        setInputValue(text);
        return;
      }
      if (!res.ok) {
        setError("Something went wrong. Please try again.");
        setMessages((prev) => prev.slice(0, -1));
        setInputValue(text);
        return;
      }
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer ?? "" }]);
      setChatRemaining(data.chat_remaining ?? (plan === "lifetime" ? null : 0));
    } catch {
      setError("Network error. Please try again.");
      setMessages((prev) => prev.slice(0, -1));
      setInputValue(text);
    } finally {
      setLoading(false);
    }
  };

  const proLimitReached = plan === "pro" && chatRemaining !== null && chatRemaining <= 0;

  const fab = (
    <button
      type="button"
      onClick={handleFabClick}
      className="fixed bottom-6 right-6 z-[98] flex items-center gap-2 px-4 py-3 rounded-2xl text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200 border border-white/10"
      style={{
        background: `linear-gradient(135deg, #0d9488 0%, ${ACCENT} 100%)`,
      }}
      aria-label={t("chat.button")}
    >
      <MessageCircle className="w-5 h-5 flex-shrink-0" strokeWidth={2} />
      <span className="hidden sm:inline max-w-[200px] truncate">{t("chat.button")}</span>
    </button>
  );

  const lockedModal = openLockedModal
    ? createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div
            className="w-full max-w-md rounded-2xl bg-[#101217]/95 border border-white/10 shadow-2xl overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chat-locked-title"
          >
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#00ffe8]/20" style={{ color: ACCENT }}>
                  <MessageCircle className="w-5 h-5" />
                </div>
                <div>
                  <h2 id="chat-locked-title" className="font-bold text-white">{t("chat.title")}</h2>
                  <p className="text-xs text-zinc-400">{matchLabel}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpenLockedModal(false)}
                className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-full bg-zinc-700/50 flex items-center justify-center mb-4">
                <Lock className="w-8 h-8" style={{ color: ACCENT }} />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">{t("chat.premiumTitle")}</h3>
              <p className="text-sm text-zinc-400 mb-6">{t("chat.premiumDesc")}</p>
              <button
                type="button"
                onClick={handleUnlockClick}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-[#0a0a0a] transition-all"
                style={{ background: ACCENT }}
              >
                <Crown className="w-5 h-5" />
                {t("chat.unlock")}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )
    : null;

  const chatPanel = openChatPanel
    ? createPortal(
        <div className="fixed inset-0 z-[100] flex flex-col sm:items-end sm:justify-end sm:p-4">
          <div className="absolute inset-0 bg-black/40 sm:bg-transparent" onClick={() => setOpenChatPanel(false)} aria-hidden />
          <div className="relative w-full sm:max-w-md sm:max-h-[85vh] sm:rounded-2xl bg-[#101217]/95 border border-white/10 shadow-2xl flex flex-col flex-1 sm:flex-initial sm:min-h-[400px] max-h-[90vh]">
            <div className="flex items-center justify-between p-4 border-b border-white/5 flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#00ffe8]/20" style={{ color: ACCENT }}>
                  <MessageCircle className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-bold text-white">{t("chat.title")}</h2>
                  <p className="text-xs text-zinc-400 truncate max-w-[220px]">{matchLabel}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpenChatPanel(false)}
                className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
              {messages.length === 0 && !error && (
                <p className="text-sm text-zinc-500">{t("chat.hint")}</p>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                      m.role === "user"
                        ? "bg-[#00ffe8]/20 text-white"
                        : "bg-zinc-800/80 text-zinc-200"
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-xl px-3 py-2 text-sm bg-zinc-800/80 text-zinc-400">…</div>
                </div>
              )}
              {error && (
                <p className="text-sm text-amber-400">{error}</p>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="p-4 border-t border-white/5 flex-shrink-0">
              {(plan === "pro" || plan === "lifetime") && (
                <p className="text-xs text-zinc-500 mb-2">
                  {plan === "lifetime" || chatRemaining === null
                    ? t("chat.unlimited")
                    : chatRemaining > 0
                      ? t("chat.oneLeft")
                      : t("chat.limitReached")}
                </p>
              )}
              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={t("chat.placeholder")}
                  rows={1}
                  disabled={loading || proLimitReached}
                  className="flex-1 min-h-[44px] max-h-24 resize-none rounded-xl bg-zinc-800/80 border border-white/10 px-3 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#00ffe8]/50 disabled:opacity-60"
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={loading || !inputValue.trim() || proLimitReached}
                  className="flex-shrink-0 h-11 w-11 rounded-xl flex items-center justify-center text-white disabled:opacity-50 transition-all"
                  style={{ background: ACCENT }}
                  aria-label={t("chat.send")}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )
    : null;

  const pricingModal = (
    <UnlockPricingModal
      open={openPricingModal}
      onClose={() => setOpenPricingModal(false)}
      variant={"pro_lifetime" as PricingModalVariant}
    />
  );

  return (
    <>
      {fab}
      {lockedModal}
      {chatPanel}
      {pricingModal}
    </>
  );
}
