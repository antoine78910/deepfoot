import { headers } from "next/headers";
import { AppBasePathProvider } from "@/contexts/AppBasePathContext";
import { AppLayoutClient } from "./AppLayoutClient";

function getAppBasePath(host: string | null): string {
  return host?.startsWith("app.") ? "" : "/app";
}

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const host = headersList.get("host") ?? "";
  const basePath = getAppBasePath(host);

  return (
    <AppBasePathProvider basePath={basePath}>
      <AppLayoutClient>{children}</AppLayoutClient>
    </AppBasePathProvider>
  );
}
