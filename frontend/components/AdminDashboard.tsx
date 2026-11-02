"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { displayNameFromEmail, getUserFromStorage, setAuthCookie, setUserInStorage } from "@/lib/auth";
import { getSignInHref } from "@/lib/app-url";
import { getApiUrl } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
const ADMIN_TOKEN_COOKIE = "deepfoot_admin_token";
const COOKIE_MAX_AGE_DAYS = 30;
const OWNER_EMAIL = "anto.delbos@gmail.com";

function getAdminTokenCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(?:^|;\\s*)" + encodeURIComponent(ADMIN_TOKEN_COOKIE) + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : "";
}

function setAdminTokenCookie(value: string) {
  if (typeof document === "undefined") return;
  const maxAge = COOKIE_MAX_AGE_DAYS * 24 * 60 * 60;
  document.cookie = `${encodeURIComponent(ADMIN_TOKEN_COOKIE)}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Strict`;
}

type AdminUser = {
  user_id: string;
  email?: string | null;
  plan: string;
  analyses_today: number;
  analyses_total: number;
  analyses_last_days: number;
  last_analysis_date?: string | null;
  recent_matches?: string[];
};

type AdminSummary = {
  window_days: number;
  feedback_count: number;
  feedback: Array<{
    id: number;
    created_at?: string;
    user_id?: string | null;
    home_team?: string | null;
    away_team?: string | null;
    page?: string | null;
    email?: string | null;
    message?: string;
  }>;
  users_count: number;
  users: AdminUser[];
  top_requested_matches: Array<{ match: string; count: number }>;
};

type PredictionCard = {
  id?: string | number;
  created_at?: string;
  home_team?: string | null;
  away_team?: string | null;
  league?: string | null;
  home_logo?: string | null;
  away_logo?: string | null;
  prob_home?: number | null;
  prob_draw?: number | null;
  prob_away?: number | null;
  most_likely_score?: string | null;
  most_likely_score_pct?: number | null;
  quick_summary?: string | null;
  source?: string;
};

function pct(n?: number | null) {
  if (typeof n !== "number" || Number.isNaN(n)) return "—";
  return `${n.toFixed(1)}%`;
}

export function AdminDashboard() {
  const [token, setToken] = useState("");
  const [days, setDays] = useState(30);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [data, setData] = useState<AdminSummary | null>(null);
  const [sessionAdmin, setSessionAdmin] = useState(false);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [predictions, setPredictions] = useState<PredictionCard[] | null>(null);
  const [predCount, setPredCount] = useState<number | null>(null);
  const [predStatus, setPredStatus] = useState<"idle" | "loading" | "error">("idle");

  const adminHeaders = useCallback((): Record<string, string> => {
    const headers: Record<string, string> = {};
    const t = token.trim() || getAdminTokenCookie();
    if (t) headers["X-Admin-Key"] = t;
    const user = getUserFromStorage();
    if (user?.id) headers["X-User-Id"] = user.id;
    return headers;
  }, [token]);

  const load = useCallback(async () => {
    setStatus("loading");
    setErrorMsg("");
    try {
      const params = new URLSearchParams({ days: String(days) });
      if (query.trim()) params.set("q", query.trim());
      const res = await fetch(`${getApiUrl()}/internal/admin/summary?${params}`, {
        headers: adminHeaders(),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Request failed");
      }
      const json = (await res.json()) as AdminSummary;
      setData(json);
      if (token.trim()) setAdminTokenCookie(token.trim());
      setStatus("idle");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Could not load admin data");
    }
  }, [adminHeaders, days, query, token]);

  useEffect(() => {
    let cancelled = false;
    const cookie = getAdminTokenCookie();
    if (cookie) setToken(cookie);

    const boot = async () => {
      let user = getUserFromStorage();
      if (!user?.id) {
        try {
          const supabase = getSupabaseBrowserClient();
          const { data } = await supabase.auth.getSession();
          const su = data.session?.user;
          if (su?.id) {
            user = {
              id: su.id,
              email: su.email || "",
              displayName:
                (su.user_metadata as { full_name?: string; name?: string } | undefined)?.full_name ||
                (su.user_metadata as { full_name?: string; name?: string } | undefined)?.name ||
                displayNameFromEmail(su.email || "admin"),
              plan: "free",
            };
            setUserInStorage(user);
            setAuthCookie();
          }
        } catch {
          // stay on stored session if Supabase is unavailable
        }
      }
      const uid = user?.id;
      if (uid) {
        try {
          const res = await fetch(`${getApiUrl()}/internal/admin/session`, {
            headers: { "X-User-Id": uid },
          });
          const payload = res.ok ? await res.json() : null;
          if (!cancelled && payload?.admin) {
            setSessionAdmin(true);
            setSessionEmail(payload.email || user?.email || null);
            return;
          }
        } catch {
          // fall through to token cookie
        }
      }
      if (!cancelled && cookie) {
        void load();
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (sessionAdmin) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionAdmin]);

  const openUser = async (u: AdminUser) => {
    setSelected(u);
    setPredictions(null);
    setPredCount(null);
    setPredStatus("loading");
    try {
      const res = await fetch(`${getApiUrl()}/internal/admin/users/${encodeURIComponent(u.user_id)}/predictions?limit=150`, {
        headers: adminHeaders(),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setPredictions(Array.isArray(json.predictions) ? json.predictions : []);
      setPredCount(typeof json.predictions_count === "number" ? json.predictions_count : null);
      setPredStatus("idle");
    } catch {
      setPredStatus("error");
    }
  };

  const users = useMemo(() => data?.users || [], [data]);
  const signInHref = `${getSignInHref()}?next=${encodeURIComponent("/admin")}`;

  return (
    <div className="min-h-screen bg-[#0d0d12] text-white p-6 md:p-10">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Signed in as <span className="text-white">{sessionEmail || OWNER_EMAIL}</span> to inspect user predictions and lifetime analysis counts.
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-[#14141c] p-4 space-y-3">
          {sessionAdmin ? (
            <p className="text-sm text-emerald-400">Admin session active{sessionEmail ? ` (${sessionEmail})` : ""}.</p>
          ) : (
            <p className="text-sm text-zinc-400">
              Sign in with <span className="text-white">{OWNER_EMAIL}</span>{" "}
              <a href={signInHref} className="text-[#00ffe8] underline">
                here
              </a>
              , or use the admin token.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {!sessionAdmin && (
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Admin token"
                className="min-w-[220px] flex-1 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
              />
            )}
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search email, plan, match…"
              className="min-w-[200px] flex-1 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
            />
            <input
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value || 30))}
              className="w-24 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
              title="Window in days"
            />
            <button
              type="button"
              onClick={() => void load()}
              disabled={status === "loading" || (!sessionAdmin && !token.trim())}
              className="rounded-lg bg-[#00ffe8] text-[#0d0d12] px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {status === "loading" ? "Loading..." : "Load"}
            </button>
          </div>
          {status === "error" && <p className="text-xs text-rose-400">{errorMsg}</p>}
        </div>

        {data && (
          <>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Users</p>
                <p className="text-xl font-semibold">{data.users_count}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Feedback</p>
                <p className="text-xl font-semibold">{data.feedback_count}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Window</p>
                <p className="text-xl font-semibold">{data.window_days} days</p>
              </div>
            </div>

            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <h2 className="text-lg font-semibold mb-3">Most requested matches</h2>
              <div className="space-y-1 text-sm">
                {data.top_requested_matches.length === 0 && <p className="text-zinc-500">No match data yet.</p>}
                {data.top_requested_matches.map((m, i) => (
                  <p key={`${m.match}-${i}`} className="text-zinc-300">
                    <span className="text-zinc-500 mr-2">#{i + 1}</span>
                    {m.match} <span className="text-[#00ffe8]">({m.count})</span>
                  </p>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <h2 className="text-lg font-semibold mb-1">Users and predictions</h2>
              <p className="text-xs text-zinc-500 mb-3">Click a row to open every analysis that user ran, and how many they have done in total.</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-zinc-500">
                    <tr>
                      <th className="text-left py-2 pr-4">Email</th>
                      <th className="text-left py-2 pr-4">Plan</th>
                      <th className="text-left py-2 pr-4">Today</th>
                      <th className="text-left py-2 pr-4">Total analyses</th>
                      <th className="text-left py-2 pr-4">Last {data.window_days}d</th>
                      <th className="text-left py-2 pr-4">Recent matches</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr
                        key={u.user_id}
                        className={`border-t border-white/5 cursor-pointer hover:bg-white/5 ${selected?.user_id === u.user_id ? "bg-white/5" : ""}`}
                        onClick={() => void openUser(u)}
                      >
                        <td className="py-2 pr-4">{u.email || "—"}</td>
                        <td className="py-2 pr-4 capitalize">{u.plan}</td>
                        <td className="py-2 pr-4">{u.analyses_today}</td>
                        <td className="py-2 pr-4 font-semibold text-[#00ffe8]">{u.analyses_total}</td>
                        <td className="py-2 pr-4">{u.analyses_last_days}</td>
                        <td className="py-2 pr-4 text-zinc-400">{(u.recent_matches || []).slice(0, 4).join(" • ") || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {selected && (
              <section className="rounded-xl border border-[#00ffe8]/30 bg-[#14141c] p-4">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
                  <div>
                    <h2 className="text-lg font-semibold">
                      {selected.email || selected.user_id}
                    </h2>
                    <p className="text-xs text-zinc-400">
                      Plan <span className="capitalize text-white">{selected.plan}</span>
                      {" · "}
                      {predCount ?? selected.analyses_total} analyses in total
                      {predictions && predCount && predictions.length < predCount
                        ? ` · showing last ${predictions.length}`
                        : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(null);
                      setPredictions(null);
                    }}
                    className="text-xs text-zinc-400 hover:text-white"
                  >
                    Close
                  </button>
                </div>
                {predStatus === "loading" && <p className="text-sm text-zinc-400">Loading predictions…</p>}
                {predStatus === "error" && <p className="text-sm text-rose-400">Could not load this user&apos;s predictions.</p>}
                {predStatus === "idle" && predictions && predictions.length === 0 && (
                  <p className="text-sm text-zinc-500">No saved predictions for this user.</p>
                )}
                <div className="space-y-3">
                  {(predictions || []).map((p, i) => (
                    <div key={String(p.id ?? i)} className="rounded-lg border border-white/10 bg-[#1c1c28] p-3">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        {p.home_logo ? <img src={p.home_logo} alt="" className="w-6 h-6 object-contain" /> : null}
                        <p className="font-semibold">
                          {p.home_team || "?"} vs {p.away_team || "?"}
                        </p>
                        {p.away_logo ? <img src={p.away_logo} alt="" className="w-6 h-6 object-contain" /> : null}
                        {p.league ? <span className="text-xs text-zinc-500">{p.league}</span> : null}
                      </div>
                      <p className="text-xs text-zinc-500 mb-2">
                        {p.created_at ? new Date(p.created_at).toLocaleString() : "—"}
                        {p.most_likely_score ? ` · most likely ${p.most_likely_score}` : ""}
                        {typeof p.most_likely_score_pct === "number" ? ` (${p.most_likely_score_pct}%)` : ""}
                      </p>
                      <p className="text-sm text-zinc-300">
                        1 {pct(p.prob_home)} · X {pct(p.prob_draw)} · 2 {pct(p.prob_away)}
                      </p>
                      {p.quick_summary ? (
                        <p className="text-xs text-zinc-400 mt-2 whitespace-pre-wrap">{p.quick_summary}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <h2 className="text-lg font-semibold mb-3">Feedback</h2>
              <div className="space-y-3">
                {data.feedback.length === 0 && <p className="text-zinc-500 text-sm">No feedback yet.</p>}
                {data.feedback.map((f) => (
                  <div key={f.id} className="rounded-lg border border-white/10 bg-[#1c1c28] p-3">
                    <p className="text-xs text-zinc-500 mb-1">
                      {f.created_at || "—"} · user={f.user_id || "anon"} · {f.home_team || "?"} vs {f.away_team || "?"} · {f.email || "no-email"}
                    </p>
                    <p className="text-sm text-zinc-200 whitespace-pre-wrap">{f.message}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
