"use client";

import { useLanguage } from "@/contexts/LanguageContext";
import { Lang } from "@/lib/translations";

export default function SettingsPage() {
  const { t, lang, setLang } = useLanguage();

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-2xl font-bold text-white">{t("settings.title")}</h1>
      <p className="text-zinc-500 mt-1">{t("settings.subtitle")}</p>

      <div className="mt-8 rounded-2xl bg-dark-card border border-dark-border p-6">
        <label className="block text-sm font-medium text-zinc-300 mb-2">
          {t("settings.language")}
        </label>
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value as Lang)}
          className="w-full max-w-xs rounded-xl bg-dark-input border border-dark-border px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-accent-green"
        >
          <option value="en">English</option>
          <option value="fr">Français</option>
        </select>
      </div>
    </div>
  );
}
