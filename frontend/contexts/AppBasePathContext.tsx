"use client";

import { createContext, useContext } from "react";

/** Base path for app routes: "" on app subdomain (app.localhost, app.deepfoot.ai), "/app" on main domain */
export const AppBasePathContext = createContext<string>("/app");

export function useAppBasePath(): string {
  return useContext(AppBasePathContext);
}

export function AppBasePathProvider({
  basePath,
  children,
}: {
  basePath: string;
  children: React.ReactNode;
}) {
  return (
    <AppBasePathContext.Provider value={basePath}>
      {children}
    </AppBasePathContext.Provider>
  );
}
