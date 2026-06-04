import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RUHI Chat — 10 Indian languages",
  description: "Multilingual AI chatbot. Type in any Indian language, reply in the same.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Noto Sans family — Indic script support without shipping Inter. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href={
            "https://fonts.googleapis.com/css2?" +
            [
              "family=Noto+Sans:wght@400;500;600;700&display=swap",
              "family=Noto+Sans+Devanagari:wght@400;500;600&display=swap",
              "family=Noto+Sans+Telugu:wght@400;500;600&display=swap",
              "family=Noto+Sans+Tamil:wght@400;500;600&display=swap",
              "family=Noto+Sans+Kannada:wght@400;500;600&display=swap",
              "family=Noto+Sans+Malayalam:wght@400;500;600&display=swap",
              "family=Noto+Sans+Bengali:wght@400;500;600&display=swap",
              "family=Noto+Sans+Gujarati:wght@400;500;600&display=swap",
              "family=Noto+Sans+Gurmukhi:wght@400;500;600&display=swap",
              "family=Noto+Sans+Oriya:wght@400;500;600&display=swap",
            ].join("&")
          }
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
