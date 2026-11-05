import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "AdalatNama", template: "%s · AdalatNama" },
  description: "Case diary and cause lists for litigation chambers.",
  applicationName: "AdalatNama",
  appleWebApp: { capable: true, title: "AdalatNama", statusBarStyle: "default" },
  icons: { apple: "/icons/apple-touch-icon.png" },
  // A private tool: keep every page out of search engines.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#12343b" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1a1c" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
