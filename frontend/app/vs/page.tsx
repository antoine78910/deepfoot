import { redirect } from "next/navigation";

export default function VsPage({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const params = new URLSearchParams();
  if (searchParams?.home) params.set("home", String(searchParams.home));
  if (searchParams?.away) params.set("away", String(searchParams.away));
  const qs = params.toString();
  redirect("/analyse" + (qs ? "?" + qs : ""));
}
