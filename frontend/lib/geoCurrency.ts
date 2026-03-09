/**
 * Map country code (from IP) to currency for pricing.
 * GBP: UK (symbol left). EUR: Europe (symbol right). USD: rest (symbol left).
 */

export type PricingCurrency = "GBP" | "EUR" | "USD";

// "Europe" here is pricing-based (EUR for Europe, GBP for UK). It's intentionally broader than the Eurozone.
const EUROPE = new Set([
  "AL", "AD", "AM", "AT", "AZ",
  "BA", "BE", "BG", "BY",
  "CH", "CY", "CZ",
  "DE", "DK",
  "EE", "ES",
  "FI", "FO", "FR",
  "GE", "GI", "GR",
  "HR", "HU",
  "IE", "IS", "IT",
  "JE",
  "LI", "LT", "LU", "LV",
  "MC", "MD", "ME", "MK", "MT",
  "NL", "NO",
  "PL", "PT",
  "RO", "RS", "RU",
  "SE", "SI", "SK", "SM",
  "TR",
  "UA",
  "VA",
  "XK",
]);

export function getCurrencyFromCountry(countryCode: string | null): PricingCurrency {
  if (!countryCode || countryCode.length !== 2) return "USD";
  const cc = countryCode.toUpperCase();
  if (cc === "GB") return "GBP";
  if (EUROPE.has(cc)) return "EUR";
  return "USD";
}

export type CurrencyConfig = {
  currency: PricingCurrency;
  symbol: string;
  symbolLeft: boolean;
  starterAmount: number;
  proAmount: number;
  lifetimeAmount: number;
  starterSuffix: string;
  proSuffix: string;
  lifetimeSuffix: string;
  saveText: string;
};

const CONFIGS: Record<PricingCurrency, CurrencyConfig> = {
  GBP: {
    currency: "GBP",
    symbol: "£",
    symbolLeft: true,
    starterAmount: 9,
    proAmount: 19,
    lifetimeAmount: 99,
    starterSuffix: "/month",
    proSuffix: "/month",
    lifetimeSuffix: " one time",
    saveText: "Save +£100/year vs monthly",
  },
  EUR: {
    currency: "EUR",
    symbol: "€",
    symbolLeft: false,
    starterAmount: 9,
    proAmount: 19,
    lifetimeAmount: 99,
    starterSuffix: "/month",
    proSuffix: "/month",
    lifetimeSuffix: " one time",
    saveText: "Save +€100/year vs monthly",
  },
  USD: {
    currency: "USD",
    symbol: "$",
    symbolLeft: true,
    starterAmount: 9,
    proAmount: 19,
    lifetimeAmount: 99,
    starterSuffix: "/month",
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
