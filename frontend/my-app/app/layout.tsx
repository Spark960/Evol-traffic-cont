import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ATSC — Evolutionary Traffic Signal Control",
  description: "GA vs Fixed-Time side-by-side traffic simulation dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}