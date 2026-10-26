import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "@/components/design-system/ThemeProvider";
import { Navbar } from "@/components/layout/Navbar";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://neuroflow.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "NeuroFlow | Autonomous AI Productivity Agent",
    template: "%s | NeuroFlow",
  },
  description:
    "Autonomous goal decomposition and deterministic daily scheduling with staged plan diffs and instant rollbacks.",
  applicationName: "NeuroFlow",
  keywords: [
    "AI Productivity",
    "Deterministic Scheduling",
    "Smart Calendar",
    "Goal Decomposition",
    "Time Blocking",
    "NeuroFlow",
  ],
  authors: [{ name: "NeuroFlow Team" }],
  creator: "NeuroFlow",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: "NeuroFlow | Autonomous AI Productivity Agent",
    description:
      "Autonomous goal decomposition and deterministic daily scheduling with staged plan diffs and instant rollbacks.",
    url: siteUrl,
    siteName: "NeuroFlow",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "NeuroFlow | Autonomous AI Productivity Agent",
    description:
      "Autonomous goal decomposition and deterministic daily scheduling with staged plan diffs and instant rollbacks.",
    creator: "@neuroflow",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body className="antialiased min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] selection:bg-[var(--accent)] selection:text-white transition-colors duration-200">
        <ThemeProvider>
          <div className="min-h-screen flex flex-col bg-[var(--bg-primary)]">
            <Navbar />
            <main className="flex-1 w-full pt-12">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

