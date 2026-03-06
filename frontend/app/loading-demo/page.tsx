"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { AnalysisStepDisplay } from "@/components/AnalysisStepDisplay";

const DEMO_STEPS = [
  "Resolving teams…",
  "Fetching team info…",
  "Fetching team form…",
  "Fetching head-to-head…",
  "Computing features…",
  "Computing probabilities…",
  "Fetching news…",
  "Generating AI summary…",
  "Done",
];

/** Random duration between 1000–2000 ms for each step */
function randomStepDuration() {
  return 1000 + Math.floor(Math.random() * 1000);
}

function LoaderSpinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className ?? "w-5 h-5"}`} fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

export default function LoadingDemoPage() {
  const [stepIndex, setStepIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const steps = DEMO_STEPS;
    const percentPerStep = 100 / Math.max(1, steps.length - 1);

    function tick() {
      setStepIndex((prev) => {
        const next = (prev + 1) % steps.length;
        const targetPercent = next === 0 ? 0 : Math.min(100, Math.round(next * percentPerStep));
        setProgress(targetPercent);
        timeoutRef.current = setTimeout(tick, randomStepDuration());
        return next;
      });
    }

    timeoutRef.current = setTimeout(tick, randomStepDuration());
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const currentStep = DEMO_STEPS[stepIndex] ?? "Initializing…";
  const displayPercent = stepIndex === 0 && progress === 0 ? 0 : progress;

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl bg-[#14141c] border border-white/10 p-8 shadow-xl">
        <h1 className="text-white text-lg font-semibold mb-6 text-center">Analysis loading preview</h1>
        <p className="text-zinc-500 text-sm text-center mb-8">Steps rotate every 1–2s (loop)</p>

        <div className="flex flex-col items-center gap-4 w-full">
          <span className="flex items-center gap-2 text-white">
            <LoaderSpinner className="w-5 h-5 flex-shrink-0 text-[#00ffe8]" />
            <span className="font-semibold">Analyzing…</span>
          </span>
          <span className="text-2xl font-bold tabular-nums text-white">{displayPercent}%</span>
          <AnalysisStepDisplay
            step={currentStep}
            variant="default"
            className="w-full min-h-[2rem] text-zinc-300"
          />
          <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-[#00ffe8] to-emerald-400 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${displayPercent}%` }}
            />
          </div>
        </div>

        <p className="text-zinc-600 text-xs text-center mt-8">
          <Link href="/" className="text-[#00ffe8] hover:underline">Back to home</Link>
          {" · "}
          <Link href="/app/matches" className="text-[#00ffe8] hover:underline">Matches</Link>
        </p>
      </div>
    </div>
  );
}
