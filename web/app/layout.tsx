import type { Metadata } from "next";
import { LanguageProvider } from "@/lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "Asisten Dokumen Internal",
  description:
    "Unggah SOP atau handbook, lalu tanyakan isinya. Jawaban disertai kutipan ke bagian dokumen asal, dengan validasi sitasi di sisi server.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="h-full antialiased">
      {/*
        suppressHydrationWarning is scoped to this element's own attributes, so
        it silences extensions that stamp <body> before React hydrates (ad
        blockers, antivirus, password managers) without hiding real mismatches
        in any child component.
      */}
      {/*
        No theme boot script here on purpose. First paint follows the OS
        preference via `prefers-color-scheme`; a stored override is applied by
        useTheme just after mount. That leaves a brief flash only for visitors
        who picked a theme differing from their OS — a smaller cost than an
        inline script, which React logs as an error on every render in this
        Next version.
      */}
      <body className="flex min-h-full flex-col" suppressHydrationWarning>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
