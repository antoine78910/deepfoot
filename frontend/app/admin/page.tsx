"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_TOKEN_COOKIE = "deepfoot_admin_token";
const COOKIE_MAX_AGE_DAYS = 30;

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
  users: Array<{
    user_id: string;
    email?: string | null;
    plan: string;
    analyses_today: number;
    analyses_total: number;
    analyses_last_days: number;
    last_analysis_date?: string | null;
    recent_matches?: string[];
  }>;
  top_requested_matches: Array<{ match: string; count: number }>;
};

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [days, setDays] = useState(30);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [data, setData] = useState<AdminSummary | null>(null);

  useEffect(() => {
    setToken(getAdminTokenCookie());
  }, []);

  const load = async () => {
    setStatus("loading");
    setErrorMsg("");
    try {
      const res = await fetch(`${API_URL}/internal/admin/summary?days=${days}`, {
        headers: { "X-Admin-Key": token.trim() },
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Request failed");
      }
      const json = (await res.json()) as AdminSummary;
      setData(json);
      setAdminTokenCookie(token.trim());
      setStatus("idle");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Could not load admin data");
    }
  };

  const topUsers = useMemo(() => (data?.users || []).slice(0, 20), [data]);

  return (
    <main className="min-h-screen bg-[#0d0d12] text-white p-6 md:p-10">
      <div className="max-w-6xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        <div className="rounded-xl border border-white/10 bg-[#14141c] p-4 space-y-3">
          <p className="text-sm text-zinc-400">Enter token to access feedback and analytics.</p>
          <div className="flex flex-wrap gap-2">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Admin token"
              className="min-w-[260px] flex-1 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
            />
            <input
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value || 30))}
              className="w-28 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={load}
              disabled={status === "loading" || !token.trim()}
              className="rounded-lg bg-[#00ffe8] text-[#0d0d12] px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {status === "loading" ? "Loading..." : "Load admin data"}
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
                <p className="text-zinc-400 text-xs">Feedback count</p>
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
              <h2 className="text-lg font-semibold mb-3">Users analytics</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-zinc-500">
                    <tr>
                      <th className="text-left py-2 pr-4">Email (app)</th>
                      <th className="text-left py-2 pr-4">Plan</th>
                      <th className="text-left py-2 pr-4">Today</th>
                      <th className="text-left py-2 pr-4">Total</th>
                      <th className="text-left py-2 pr-4">Last {data.window_days}d</th>
                      <th className="text-left py-2 pr-4">Recent matches</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topUsers.map((u) => (
                      <tr key={u.user_id} className="border-t border-white/5">
                        <td className="py-2 pr-4 text-sm">{u.email || u.user_id}</td>
                        <td className="py-2 pr-4">{u.plan}</td>
                        <td className="py-2 pr-4">{u.analyses_today}</td>
                        <td className="py-2 pr-4">{u.analyses_total}</td>
                        <td className="py-2 pr-4">{u.analyses_last_days}</td>
                        <td className="py-2 pr-4 text-zinc-400">{(u.recent_matches || []).slice(0, 3).join(" • ") || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

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
    </main>
  );
}
