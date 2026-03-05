"use client";

import { InfiniteSlider } from "@/components/ui/infinite-slider";

/** 26 league logos for LP horizontal scroll. Place PNGs in public/lp-logos/ as logo-1.png … logo-26.png */
const LEAGUE_LOGOS = [
  { src: "/lp-logos/logo-1.png", alt: "UEFA Champions League" },
  { src: "/lp-logos/logo-2.png", alt: "Emirates FA Cup" },
  { src: "/lp-logos/logo-3.png", alt: "UEFA Europa League" },
  { src: "/lp-logos/logo-4.png", alt: "Bundesliga" },
  { src: "/lp-logos/logo-5.png", alt: "Serie A" },
  { src: "/lp-logos/logo-6.png", alt: "Premier League" },
  { src: "/lp-logos/logo-7.png", alt: "Ligue 1" },
  { src: "/lp-logos/logo-8.png", alt: "Carabao Cup EFL" },
  { src: "/lp-logos/logo-9.png", alt: "Tinkoff Russian Premier Liga" },
  { src: "/lp-logos/logo-10.png", alt: "Allsvenskan" },
  { src: "/lp-logos/logo-11.png", alt: "Copa del Rey" },
  { src: "/lp-logos/logo-12.png", alt: "Bundesliga" },
  { src: "/lp-logos/logo-13.png", alt: "Hrvatski Telekom Prva Liga" },
  { src: "/lp-logos/logo-14.png", alt: "Eredivisie" },
  { src: "/lp-logos/logo-15.png", alt: "Jupiler Pro League" },
  { src: "/lp-logos/logo-16.png", alt: "EFL" },
  { src: "/lp-logos/logo-17.png", alt: "La Liga" },
  { src: "/lp-logos/logo-18.png", alt: "Primeira Liga" },
  { src: "/lp-logos/logo-19.png", alt: "Süper Lig" },
  { src: "/lp-logos/logo-20.png", alt: "Championship" },
  { src: "/lp-logos/logo-21.png", alt: "Saudi Pro League" },
  { src: "/lp-logos/logo-22.png", alt: "Ukrainian Premier League" },
  { src: "/lp-logos/logo-23.png", alt: "Elite Serien" },
  { src: "/lp-logos/logo-24.png", alt: "SPFL" },
  { src: "/lp-logos/logo-25.png", alt: "Süper Lig" },
  { src: "/lp-logos/logo-26.png", alt: "League logo" },
];

export function LogoCloud() {
  return (
    <div
      className="w-full overflow-hidden py-6 [--logo-size:3.5rem] sm:[--logo-size:4.5rem] md:[--logo-size:5rem]"
      style={{
        maskImage: "linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)",
        WebkitMaskImage: "linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)",
      }}
    >
      <InfiniteSlider gap={40} reverse speed={18} className="flex items-center">
        {LEAGUE_LOGOS.map((logo) => (
          <img
            alt={logo.alt}
            className="pointer-events-none h-[var(--logo-size)] w-[var(--logo-size)] select-none object-contain opacity-90 transition-opacity hover:opacity-100"
            height={48}
            key={logo.src}
            loading="lazy"
            src={logo.src}
            width={48}
            onError={(e) => {
              e.currentTarget.style.opacity = "0.3";
            }}
          />
        ))}
      </InfiniteSlider>
    </div>
  );
}
