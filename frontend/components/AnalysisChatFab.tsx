"use client";

import { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { MessageCircle, Lock, Crown, X, Send } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { getUserFromStorage, setUserInStorage, type PlanId } from "@/lib/auth";
import { getApiUrl } from "@/lib/api";
import { UnlockPricingModal, type PricingModalVariant } from "./UnlockPricingModal";
import { ChatMarkdown } from "./ChatMarkdown";

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
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

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
        const detail = typeof data.detail === "string" ? data.detail : "";
        setError(detail || t("chat.unavailable"));
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

  const fab =
    mounted && !openChatPanel
      ? createPortal(
          <button
            type="button"
            onClick={handleFabClick}
            className="fixed bottom-5 right-5 z-[98] h-14 w-14 rounded-full text-[#0d0d12] shadow-[0_8px_24px_rgba(0,255,232,0.35)] hover:scale-105 active:scale-95 transition-transform duration-200 border border-white/20 flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg, #0d9488 0%, ${ACCENT} 100%)`,
            }}
            aria-label={t("chat.button")}
            title={t("chat.button")}
          >
            <MessageCircle className="w-6 h-6" strokeWidth={2.2} />
            {!canUseChat && (
              <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-[#101217] border border-white/20 flex items-center justify-center">
                <Lock className="w-2.5 h-2.5 text-[#00ffe8]" />
              </span>
            )}
          </button>,
          document.body
        )
      : null;

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

  const chatPanel =
    mounted && openChatPanel
      ? createPortal(
          <div className="fixed inset-0 z-[100] pointer-events-none">
            <button
              type="button"
              className="absolute inset-0 pointer-events-auto bg-black/20 sm:bg-transparent"
              onClick={() => setOpenChatPanel(false)}
              aria-label="Close"
            />
            <div className="pointer-events-auto absolute left-3 right-3 bottom-3 h-[min(70vh,520px)] sm:left-auto sm:right-5 sm:bottom-5 sm:w-[360px] sm:h-[480px] rounded-2xl bg-[#101217]/95 border border-white/10 shadow-2xl flex flex-col overflow-hidden">
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
                    className={`rounded-xl px-3 py-2 text-sm ${
                      m.role === "user"
                        ? "max-w-[85%] bg-[#00ffe8]/20 text-white whitespace-pre-wrap"
                        : "max-w-[95%] bg-zinc-800/80 text-zinc-200"
                    }`}
                  >
                    {m.role === "assistant" ? <ChatMarkdown text={m.content} /> : m.content}
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
