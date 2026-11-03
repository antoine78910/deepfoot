"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AnalysisResult } from "@/components/AnalysisResult";
import { getApiUrl } from "@/lib/api";
import { displayNameFromEmail, fullAnalysisForPlan, getAdminActingUser, type PlanId } from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

const PLANS: PlanId[] = ["free", "starter", "pro", "lifetime"];

type PreviewPayload = {
  id?: string;
  user_id?: string | null;
  email?: string | null;
  plan?: string;
  created_at?: string;
  result?: Record<string, unknown>;
};

export default function AdminPredictionPreviewPage() {
  const params = useParams<{ id: string }>();
  const predictionId = String(params?.id || "");
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [error, setError] = useState("");
  const [payload, setPayload] = useState<PreviewPayload | null>(null);
  const [viewPlan, setViewPlan] = useState<PlanId>("free");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setStatus("loading");
      setError("");
      try {
        const headers: Record<string, string> = {};
        let user = getAdminActingUser();
        if (!user?.id) {
          try {
            const supabase = getSupabaseBrowserClient();
            const { data } = await supabase.auth.getSession();
            const su = data.session?.user;
            if (su?.id) {
              user = {
                id: su.id,
                email: su.email || "",
                displayName: displayNameFromEmail(su.email || "admin"),
                plan: "free",
              };
            }
          } catch {
            // ignore
          }
        }
        if (user?.id) headers["X-User-Id"] = user.id;
        if (user?.email) headers["X-User-Email"] = user.email;
        const res = await fetch(`${getApiUrl()}/internal/admin/predictions/${encodeURIComponent(predictionId)}`, {
          headers,
        });
        if (!res.ok) throw new Error((await res.text()) || "Could not load prediction");
        const json = (await res.json()) as PreviewPayload;
        if (cancelled) return;
        setPayload(json);
        const plan = (json.plan || "free").toLowerCase() as PlanId;
        setViewPlan(PLANS.includes(plan) ? plan : "free");
        setStatus("ready");
      } catch (e) {
        if (cancelled) return;
        setStatus("error");
        setError(e instanceof Error ? e.message : "Could not load prediction");
      }
    };
    if (predictionId) void load();
    return () => {
      cancelled = true;
    };
  }, [predictionId]);

  const resultToShow = useMemo(() => {
    if (!payload?.result) return null;
    return { ...payload.result, full_analysis: fullAnalysisForPlan(viewPlan) };
  }, [payload, viewPlan]);

  const matchLabel = [payload?.result?.home_team, payload?.result?.away_team].filter(Boolean).join(" vs ") || "Match";

  return (
    <div className="min-h-screen bg-[#09090f] text-white">
      <div className="sticky top-0 z-40 border-b border-white/10 bg-[#0f0f16]/95 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3">
          <Link href="/admin" className="text-sm text-zinc-400 hover:text-white">
            ← Admin
          </Link>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate">{matchLabel}</p>
            <p className="text-xs text-zinc-500 truncate">
              Viewing as {payload?.email || payload?.user_id || "anonymous"} · account plan{" "}
              <span className="capitalize text-zinc-300">{payload?.plan || "free"}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-1">
            {PLANS.map((plan) => (
              <button
                key={plan}
                type="button"
                onClick={() => setViewPlan(plan)}
                className={`rounded-full px-2.5 py-1 text-xs capitalize ${
                  viewPlan === plan ? "bg-[#00ffe8] text-[#0d0d12] font-semibold" : "bg-white/5 text-zinc-300 hover:bg-white/10"
                }`}
              >
                {plan}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-4xl mx-auto px-4 py-6">
        {status === "loading" && <p className="text-zinc-400">Loading prediction…</p>}
        {status === "error" && <p className="text-rose-400 text-sm">{error || "Prediction not found."}</p>}
        {status === "ready" && resultToShow ? (
          <AnalysisResult result={resultToShow} hideChat />
        ) : null}
      </div>
    </div>
  );
}
