// The frame around every page: fonts, the shared settings, the header and the tab bar.
// Next.js puts the current page where {children} is. When you click another tab, only
// {children} changes; the header, the tab bar and the settings stay on screen.

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import NavTabs from "@/components/NavTabs";
import SettingsProvider from "@/components/SettingsProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// The browser tab title and the description search engines show.
export const metadata: Metadata = {
  title: "CourtForecastNBA",
  description: "Predicts every remaining NBA game, the standings and the champion.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">
        <SettingsProvider>
          <div className="mx-auto max-w-7xl px-4 py-6">
            <Header />
            <NavTabs />
            <main>{children}</main>
          </div>
        </SettingsProvider>
      </body>
    </html>
  );
}
