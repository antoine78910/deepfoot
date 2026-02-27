"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnalysisResult } from "@/components/AnalysisResult";

export default function AnalysisPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("visifoot_analysis");
    if (raw) {
      try {
        setData(JSON.parse(raw));
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
  }, []);

  if (data === null) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <p className="text-zinc-400 mb-4">No analysis data. Start by analyzing a match.</p>
        <Link href="/" className="text-[#00ffe8] hover:underline">Back to home</Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8 pb-16 max-w-4xl mx-auto">
      <Link href="/" className="inline-block text-zinc-500 hover:text-[#00ffe8] text-sm mb-8">
        ← New analysis
      </Link>
      <AnalysisResult result={data} />
    </main>
  );
}
