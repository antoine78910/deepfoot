import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false, nocache: true },
};

export default function AppAdminLayout({ children }: { children: React.ReactNode }) {
  return children;
}
