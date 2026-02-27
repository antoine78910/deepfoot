/**
 * Map country code (from IP) to currency for pricing.
 * GBP: UK (symbol left). EUR: Eurozone (symbol right). USD: rest (symbol left).
 */

export type PricingCurrency = "GBP" | "EUR" | "USD";

const EUROZONE = new Set([
  "AT", "BE", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR", "IE", "IT",
  "LT", "LU", "LV", "MT", "NL", "PT", "SK", "SI",
]);

export function getCurrencyFromCountry(countryCode: string | null): PricingCurrency {
  if (!countryCode || countryCode.length !== 2) return "USD";
  const cc = countryCode.toUpperCase();
  if (cc === "GB") return "GBP";
  if (EUROZONE.has(cc)) return "EUR";
  return "USD";
}

export type CurrencyConfig = {
  currency: PricingCurrency;
  symbol: string;
  symbolLeft: boolean;
  proAmount: number;
  lifetimeAmount: number;
  proSuffix: string;
  lifetimeSuffix: string;
  saveText: string;
};

const CONFIGS: Record<PricingCurrency, CurrencyConfig> = {
  GBP: {
    currency: "GBP",
    symbol: "£",
    symbolLeft: true,
    proAmount: 16,
    lifetimeAmount: 85,
    proSuffix: "/month",
    lifetimeSuffix: " one time",
    saveText: "Save +£100/year vs monthly",
  },
  EUR: {
    currency: "EUR",
    symbol: "€",
    symbolLeft: false,
    proAmount: 19,
    lifetimeAmount: 99,
    proSuffix: "/month",
    lifetimeSuffix: " one time",
    saveText: "Save +€100/year vs monthly",
  },
  USD: {
    currency: "USD",
    symbol: "$",
    symbolLeft: true,
    proAmount: 19,
    lifetimeAmount: 99,
    proSuffix: "/month",
    lifetimeSuffix: " one time",
    saveText: "Save +$100/year vs monthly",
  },
};

export function getCurrencyConfig(currency: PricingCurrency): CurrencyConfig {
  return CONFIGS[currency];
}

export function formatPrice(config: CurrencyConfig, amount: number): string {
  if (config.symbolLeft) return `${config.symbol}${amount}`;
  return `${amount}${config.symbol}`;
}
