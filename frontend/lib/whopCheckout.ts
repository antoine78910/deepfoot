import type { PricingCurrency } from "@/lib/geoCurrency";

export type WhopPlanId = "starter" | "pro" | "lifetime";

const CHECKOUT_URLS: Record<PricingCurrency, Record<WhopPlanId, string>> = {
  // USD: countries outside UK + Europe
  USD: {
    lifetime: "https://whop.com/checkout/plan_a9qUhL4i9mz6B",
    pro: "https://whop.com/checkout/plan_OPBroVFLkZFuG",
    starter: "https://whop.com/checkout/plan_xncEV4h0yc3F1",
  },
  // GBP: UK
  GBP: {
    lifetime: "https://whop.com/checkout/plan_m9Bcvjqy3xudw",
    pro: "https://whop.com/checkout/plan_pVoGBCVIzFw4M",
    starter: "https://whop.com/checkout/plan_SosIjQXUrG5Pb",
  },
  // EUR: Europe (non-UK)
  EUR: {
    lifetime: "https://whop.com/checkout/plan_FXHgaDOloK9Q1",
    pro: "https://whop.com/checkout/plan_ASd2bXI29nfKR",
    starter: "https://whop.com/checkout/plan_WmP3L9eEPlEJb",
  },
};

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
  userEmail?: string | null
): string {
  let url = CHECKOUT_URLS[currency][plan];
  const params = new URLSearchParams();
  if (datafastVisitorId?.trim()) {
    params.set("datafast_visitor_id", datafastVisitorId.trim());
  }
  if (userEmail?.trim()) {
    params.set("email", userEmail.trim());
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

