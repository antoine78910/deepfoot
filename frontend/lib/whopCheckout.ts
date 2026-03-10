import type { PricingCurrency } from "@/lib/geoCurrency";

export type WhopPlanId = "starter" | "pro" | "lifetime";

const CHECKOUT_URLS: Record<PricingCurrency, Record<WhopPlanId, string>> = {
  // USD: countries outside UK + Europe (9 / 19.99 / 99.99)
  USD: {
    starter: "https://whop.com/checkout/plan_XNiSpw7OKJoIi",
    pro: "https://whop.com/checkout/plan_LwCFHHdytBkM6",
    lifetime: "https://whop.com/checkout/plan_MlCRcQibssX37",
  },
  // GBP: UK (9 / 19 / 99)
  GBP: {
    starter: "https://whop.com/checkout/plan_PEt1oIDXTTimX",
    pro: "https://whop.com/checkout/plan_4txPPDCv7OjiR",
    lifetime: "https://whop.com/checkout/plan_h5Om2F0ga6UhT",
  },
  // EUR: Europe non-UK (9 / 19 / 99)
  EUR: {
    starter: "https://whop.com/checkout/plan_3pzB8Vw1GIjSb",
    pro: "https://whop.com/checkout/plan_35zzQVid4lE9Z",
    lifetime: "https://whop.com/checkout/plan_ErLwV2KgiMiC1",
  },
};

/** Base URL for Whop subscription management (upgrade with proration). */
const WHOP_MANAGE_BASE = "https://whop.com/billing/manage/";

/** True when the user already has a plan and wants a higher one (Starter→Pro, Starter→Lifetime, Pro→Lifetime). Use manage URL for these so Whop applies proration. */
export function isUpgradeFromCurrentPlan(currentPlan: string, targetPlan: WhopPlanId): boolean {
  if (currentPlan === "free") return false;
  if (currentPlan === "starter") return targetPlan === "pro" || targetPlan === "lifetime";
  if (currentPlan === "pro") return targetPlan === "lifetime";
  return false;
}

/** URL for the user to manage their subscription (upgrade with proration). Uses API manage_url or builds from membership_id. */
export function getWhopManageUrl(user: { whop_manage_url?: string | null; whop_membership_id?: string | null } | null): string | null {
  if (!user) return null;
  const url = (user.whop_manage_url || "").trim();
  if (url) return url;
  const mid = (user.whop_membership_id || "").trim();
  return mid ? `${WHOP_MANAGE_BASE}${mid}` : null;
}

/** Read DataFast visitor ID from cookie (for revenue attribution). Call only in browser. */
export function getDatafastVisitorId(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/\bdatafast_visitor_id=([^;]+)/);
  return match ? decodeURIComponent(match[1].trim()) : null;
}

export function getWhopCheckoutUrl(
  plan: WhopPlanId,
  currency: PricingCurrency,
  datafastVisitorId?: string | null,
  context?: string | null,
  /** Email of the logged-in user (Supabase app). Prefills checkout to avoid mismatches. */
  userEmail?: string | null,
  /** Whop membership id when upgrading (e.g. Starter → Pro). Pass so Whop can apply proration if supported. */
  whopMembershipId?: string | null
): string {
  let url = CHECKOUT_URLS[currency][plan];
  const params = new URLSearchParams();
  if (datafastVisitorId?.trim()) {
    params.set("datafast_visitor_id", datafastVisitorId.trim());
  }
  if (userEmail?.trim()) {
    params.set("email", userEmail.trim());
    // Stripe-style prefilled identification (Whop may use it for proration on upgrade)
    params.set("prefilled_identification[email]", userEmail.trim());
  }
  if (whopMembershipId?.trim()) {
    params.set("membership_id", whopMembershipId.trim());
  }
  // Help Datafast / internal analytics distinguish flows
  params.set("df_plan", plan);
  if (context?.trim()) {
    params.set("df_source", context.trim());
  }
  params.set("allow_promotion_codes", "true");
  const qs = params.toString();
  if (qs) {
    url += url.includes("?") ? `&${qs}` : `?${qs}`;
  }
  return url;
}

