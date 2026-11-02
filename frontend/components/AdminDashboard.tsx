"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { displayNameFromEmail, getUserFromStorage, setAuthCookie, setUserInStorage, type UserInfo } from "@/lib/auth";
import { getSignInHref } from "@/lib/app-url";
import { getApiUrl } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const OWNER_EMAIL = "anto.delbos@gmail.com";

type AdminSection = "overview" | "users" | "predictions" | "feedback";

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
  user_id?: string | null;
  email?: string | null;
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

function isOwnerEmail(email?: string | null) {
  return (email || "").trim().toLowerCase() === OWNER_EMAIL;
}

function formatWhen(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

async function resolveSignedInUser(): Promise<UserInfo | null> {
  let user = getUserFromStorage();
  try {
    const supabase = getSupabaseBrowserClient();
    const { data } = await supabase.auth.getSession();
    const su = data.session?.user;
    if (su?.id) {
      user = {
        id: su.id,
        email: su.email || user?.email || "",
        displayName:
          (su.user_metadata as { full_name?: string; name?: string } | undefined)?.full_name ||
          (su.user_metadata as { full_name?: string; name?: string } | undefined)?.name ||
          displayNameFromEmail(su.email || "admin"),
        plan: user?.plan || "free",
      };
      setUserInStorage(user);
      setAuthCookie();
    }
  } catch {
    // keep localStorage user if Supabase session is missing
  }
  return user;
}

function PredictionList({
  items,
  empty,
  emailByUser,
}: {
  items: PredictionCard[];
  empty: string;
  emailByUser?: Record<string, string>;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-zinc-500">{empty}</p>;
  }
  return (
    <div className="space-y-3">
      {items.map((p, i) => {
        const email = p.email || (p.user_id ? emailByUser?.[p.user_id] : null);
        return (
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
              {formatWhen(p.created_at)}
              {email ? ` · ${email}` : ""}
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
        );
      })}
    </div>
  );
}

export function AdminDashboard() {
  const [section, setSection] = useState<AdminSection>("overview");
  const [days, setDays] = useState(30);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [data, setData] = useState<AdminSummary | null>(null);
  const [sessionAdmin, setSessionAdmin] = useState(false);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [userPredictions, setUserPredictions] = useState<PredictionCard[] | null>(null);
  const [predCount, setPredCount] = useState<number | null>(null);
  const [predStatus, setPredStatus] = useState<"idle" | "loading" | "error">("idle");
  const [allPredictions, setAllPredictions] = useState<PredictionCard[]>([]);
  const [allPredStatus, setAllPredStatus] = useState<"idle" | "loading" | "error">("idle");

  const adminHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const headers: Record<string, string> = {};
    const user = (await resolveSignedInUser()) || getUserFromStorage();
    if (user?.id) headers["X-User-Id"] = user.id;
    if (user?.email) headers["X-User-Email"] = user.email;
    return headers;
  }, []);

  const load = useCallback(async () => {
    setStatus("loading");
    setErrorMsg("");
    try {
      const headers = await adminHeaders();
      const params = new URLSearchParams({ days: String(days) });
      if (query.trim()) params.set("q", query.trim());
      const res = await fetch(`${getApiUrl()}/internal/admin/summary?${params}`, { headers });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Request failed");
      }
      const json = (await res.json()) as AdminSummary;
      setData(json);
      setStatus("idle");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Could not load admin data");
    }
  }, [adminHeaders, days, query]);

  const loadAllPredictions = useCallback(async () => {
    setAllPredStatus("loading");
    try {
      const headers = await adminHeaders();
      const params = new URLSearchParams({ limit: "250" });
      if (query.trim()) params.set("q", query.trim());
      const res = await fetch(`${getApiUrl()}/internal/admin/predictions?${params}`, { headers });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setAllPredictions(Array.isArray(json.predictions) ? json.predictions : []);
      setAllPredStatus("idle");
    } catch {
      setAllPredStatus("error");
    }
  }, [adminHeaders, query]);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      const user = await resolveSignedInUser();
      const headers: Record<string, string> = {};
      if (user?.id) headers["X-User-Id"] = user.id;
      if (user?.email) headers["X-User-Email"] = user.email;
      let admin = isOwnerEmail(user?.email);
      let email = user?.email || null;
      if (user?.id) {
        try {
          const res = await fetch(`${getApiUrl()}/internal/admin/session`, { headers });
          const payload = res.ok ? await res.json() : null;
          if (payload?.admin) {
            admin = true;
            email = payload.email || email;
          } else if (!isOwnerEmail(user.email)) {
            admin = false;
          }
        } catch {
          // owner email from the signed-in session is enough to try loading data
        }
      }
      if (cancelled) return;
      setSessionEmail(email);
      setSessionAdmin(admin);
      setBooting(false);
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionAdmin) return;
    void load();
    void loadAllPredictions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionAdmin]);

  const openUser = async (u: AdminUser) => {
    setSelected(u);
    setSection("predictions");
    setUserPredictions(null);
    setPredCount(null);
    setPredStatus("loading");
    try {
      const headers = await adminHeaders();
      const res = await fetch(
        `${getApiUrl()}/internal/admin/users/${encodeURIComponent(u.user_id)}/predictions?limit=150`,
        { headers }
      );
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setUserPredictions(Array.isArray(json.predictions) ? json.predictions : []);
      setPredCount(typeof json.predictions_count === "number" ? json.predictions_count : null);
      setPredStatus("idle");
    } catch {
      setPredStatus("error");
    }
  };

  const users = useMemo(() => data?.users || [], [data]);
  const emailByUser = useMemo(() => {
    const map: Record<string, string> = {};
    for (const u of users) {
      if (u.user_id && u.email) map[u.user_id] = u.email;
    }
    return map;
  }, [users]);
  const predictionsTotal = useMemo(
    () => users.reduce((sum, u) => sum + (u.analyses_total || 0), 0),
    [users]
  );
  const signInHref = `${getSignInHref()}?next=${encodeURIComponent("/admin")}`;

  const nav: Array<{ id: AdminSection; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "users", label: "Users" },
    { id: "predictions", label: "Predictions" },
    { id: "feedback", label: "Feedback" },
  ];

  if (booting) {
    return (
      <div className="min-h-screen bg-[#09090f] text-zinc-300 flex items-center justify-center">
        <p>Loading admin console…</p>
      </div>
    );
  }

  if (!sessionAdmin) {
    return (
      <div className="min-h-screen bg-[#09090f] text-white flex items-center justify-center p-6">
        <div className="max-w-md w-full rounded-2xl border border-white/10 bg-[#14141c] p-6 space-y-4">
          <p className="text-xs uppercase tracking-wide text-[#00ffe8]">DeepFoot admin</p>
          <h1 className="text-2xl font-bold">Admin console</h1>
          <p className="text-sm text-zinc-400">
            Sign in with <span className="text-white">{OWNER_EMAIL}</span> to open the admin dashboard.
            This is separate from the user app.
          </p>
          {sessionEmail && !isOwnerEmail(sessionEmail) ? (
            <p className="text-sm text-amber-300">
              You are signed in as {sessionEmail}. That account cannot open admin.
            </p>
          ) : null}
          <a
            href={signInHref}
            className="inline-flex rounded-lg bg-[#00ffe8] text-[#0d0d12] px-4 py-2 text-sm font-semibold"
          >
            Sign in as admin
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090f] text-white flex">
      <aside className="w-56 shrink-0 border-r border-white/10 bg-[#0f0f16] p-4 flex flex-col gap-6">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[#00ffe8]">DeepFoot</p>
          <h1 className="text-lg font-bold">Admin</h1>
          <p className="text-xs text-zinc-500 mt-1 break-all">{sessionEmail || OWNER_EMAIL}</p>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSection(item.id)}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm ${
                section === item.id ? "bg-[#00ffe8] text-[#0d0d12] font-semibold" : "text-zinc-300 hover:bg-white/5"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <a href="/" className="mt-auto text-xs text-zinc-500 hover:text-white">
          Back to site
        </a>
      </aside>

      <main className="flex-1 min-w-0 p-6 md:p-8 space-y-6">
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search email, plan, match…"
            className="min-w-[220px] flex-1 rounded-lg bg-[#1c1c28] border border-white/10 px-3 py-2 text-sm"
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
            onClick={() => {
              void load();
              void loadAllPredictions();
            }}
            disabled={status === "loading"}
            className="rounded-lg bg-[#00ffe8] text-[#0d0d12] px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {status === "loading" ? "Loading..." : "Refresh"}
          </button>
        </div>
        {status === "error" && <p className="text-sm text-rose-400">{errorMsg}</p>}

        {section === "overview" && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Users</p>
                <p className="text-2xl font-semibold">{data?.users_count ?? "—"}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Predictions generated</p>
                <p className="text-2xl font-semibold">{data ? predictionsTotal : "—"}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Feedback</p>
                <p className="text-2xl font-semibold">{data?.feedback_count ?? "—"}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-[#14141c] p-4">
                <p className="text-zinc-400 text-xs">Window</p>
                <p className="text-2xl font-semibold">{data?.window_days ?? days} days</p>
              </div>
            </div>
            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <h2 className="text-lg font-semibold mb-3">Most requested matches</h2>
              <div className="space-y-1 text-sm">
                {(data?.top_requested_matches || []).length === 0 && <p className="text-zinc-500">No match data yet.</p>}
                {(data?.top_requested_matches || []).map((m, i) => (
                  <p key={`${m.match}-${i}`} className="text-zinc-300">
                    <span className="text-zinc-500 mr-2">#{i + 1}</span>
                    {m.match} <span className="text-[#00ffe8]">({m.count})</span>
                  </p>
                ))}
              </div>
            </section>
            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">Latest predictions</h2>
                <button type="button" onClick={() => setSection("predictions")} className="text-xs text-[#00ffe8]">
                  View all
                </button>
              </div>
              <PredictionList items={allPredictions.slice(0, 8)} empty="No predictions yet." emailByUser={emailByUser} />
            </section>
          </div>
        )}

        {section === "users" && (
          <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
            <h2 className="text-lg font-semibold mb-1">Users</h2>
            <p className="text-xs text-zinc-500 mb-3">Click a row to open every prediction that user generated.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-zinc-500">
                  <tr>
                    <th className="text-left py-2 pr-4">Email</th>
                    <th className="text-left py-2 pr-4">Plan</th>
                    <th className="text-left py-2 pr-4">Today</th>
                    <th className="text-left py-2 pr-4">Total predictions</th>
                    <th className="text-left py-2 pr-4">Last {data?.window_days ?? days}d</th>
                    <th className="text-left py-2 pr-4">Recent matches</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr
                      key={u.user_id}
                      className="border-t border-white/5 cursor-pointer hover:bg-white/5"
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
        )}

        {section === "predictions" && (
          <div className="space-y-6">
            {selected && (
              <section className="rounded-xl border border-[#00ffe8]/30 bg-[#14141c] p-4">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
                  <div>
                    <h2 className="text-lg font-semibold">{selected.email || selected.user_id}</h2>
                    <p className="text-xs text-zinc-400">
                      Plan <span className="capitalize text-white">{selected.plan}</span>
                      {" · "}
                      {predCount ?? selected.analyses_total} predictions in total
                      {userPredictions && predCount && userPredictions.length < predCount
                        ? ` · showing last ${userPredictions.length}`
                        : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(null);
                      setUserPredictions(null);
                    }}
                    className="text-xs text-zinc-400 hover:text-white"
                  >
                    Show all users
                  </button>
                </div>
                {predStatus === "loading" && <p className="text-sm text-zinc-400">Loading predictions…</p>}
                {predStatus === "error" && (
                  <p className="text-sm text-rose-400">Could not load this user&apos;s predictions.</p>
                )}
                {predStatus === "idle" && (
                  <PredictionList items={userPredictions || []} empty="No saved predictions for this user." />
                )}
              </section>
            )}
            <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
              <h2 className="text-lg font-semibold mb-3">{selected ? "All other recent predictions" : "All generated predictions"}</h2>
              {allPredStatus === "loading" && <p className="text-sm text-zinc-400">Loading predictions…</p>}
              {allPredStatus === "error" && <p className="text-sm text-rose-400">Could not load predictions.</p>}
              {allPredStatus === "idle" && (
                <PredictionList items={allPredictions} empty="No predictions yet." emailByUser={emailByUser} />
              )}
            </section>
          </div>
        )}

        {section === "feedback" && (
          <section className="rounded-xl border border-white/10 bg-[#14141c] p-4">
            <h2 className="text-lg font-semibold mb-3">Feedback</h2>
            <div className="space-y-3">
              {(data?.feedback || []).length === 0 && <p className="text-zinc-500 text-sm">No feedback yet.</p>}
              {(data?.feedback || []).map((f) => (
                <div key={f.id} className="rounded-lg border border-white/10 bg-[#1c1c28] p-3">
                  <p className="text-xs text-zinc-500 mb-1">
                    {formatWhen(f.created_at)} · {f.email || f.user_id || "anon"} · {f.home_team || "?"} vs {f.away_team || "?"}
                  </p>
                  <p className="text-sm text-zinc-200 whitespace-pre-wrap">{f.message}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
