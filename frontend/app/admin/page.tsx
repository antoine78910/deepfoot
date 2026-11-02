"use client";

import { useEffect, useState } from "react";
import { AdminDashboard } from "@/components/AdminDashboard";
import { PRODUCTION_APP_ORIGIN } from "@/lib/app-url";

export default function AdminPage() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const host = window.location.hostname.toLowerCase();
    if (host === "www.deepfoot.io" || host === "deepfoot.io") {
      window.location.replace(`${PRODUCTION_APP_ORIGIN}/admin`);
      return;
    }
    setReady(true);
  }, []);

  if (!ready) {
    return (
      <main className="min-h-screen bg-[#0d0d12] text-zinc-300 p-10">
        <p>Opening the admin dashboard…</p>
      </main>
    );
  }

  return <AdminDashboard />;
}
