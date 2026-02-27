import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getAppHref } from "@/lib/app-url";

export default async function AppPage() {
  const headersList = await headers();
  const host = headersList.get("host") ?? "";
  const isAppSubdomain = host.startsWith("app.");
  redirect(isAppSubdomain ? "/history" : getAppHref("/history"));
}
