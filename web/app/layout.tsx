// The frame around every page: fonts, the shared settings, the sticky top bar.
// Next.js puts the current page where {children} is. When you click another tab, only
// {children} changes; the top bar and the settings (with the data they loaded) stay.

import type { Metadata, Viewport } from "next";
import { Archivo, Big_Shoulders } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import SettingsProvider from "@/components/SettingsProvider";

// next/font downloads these from Google Fonts at build time and serves them from this
// site, so visitors' browsers never contact Google. Each one sets a CSS variable that
// globals.css maps to Tailwind's `font-sans` and `font-display`.

/** Body text, tables and every number. Archivo has tabular (equal-width) digits, so
 *  columns of numbers line up when a class adds `tabular-nums`. */
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
});

/** The wordmark and headings: a condensed face based on Chicago's signage, with the
 *  tall, tight look of arena lettering. */
const bigShoulders = Big_Shoulders({
  variable: "--font-big-shoulders",
  subsets: ["latin"],
  // Note: `next build` warns "Failed to find font override values for Big Shoulders".
  // That only means Next.js can't build a size-matched fallback font for it; headings use
  // the system font for the split second before Big Shoulders loads. It's harmless.
});

// The browser tab title and the description search engines show.
export const metadata: Metadata = {
  title: "CourtForecastNBA",
  description: "Predicts every remaining NBA game, the standings and the champion.",
};

// The color phones use for their status bar / browser toolbar: the page's navy, so the
// app looks continuous up to the top edge of the screen.
export const viewport: Viewport = {
  themeColor: "#0a1322",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${archivo.variable} ${bigShoulders.variable} h-full antialiased`}>
      <body className="min-h-full bg-canvas font-sans text-fg">
        <SettingsProvider>
          {/* The top bar spans the full width (so it can stick to the top edge); the
              page content sits in a centered column. px-4 keeps a 16px gutter on phones;
              max-w-6xl stops lines getting too long on big screens. */}
          <Header />
          <main className="mx-auto max-w-6xl px-4 pt-10 pb-24 md:px-8 md:pt-14">{children}</main>
        </SettingsProvider>
      </body>
    </html>
  );
}
