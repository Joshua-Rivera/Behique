import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AppShell, Providers } from "@/components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: "Behique",
  description: "Search and ask questions about your own files, locally.",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
