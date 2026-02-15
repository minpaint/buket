import type { Metadata } from "next";
import "./globals.css";
import ContextProviderLayout from "@/context/context";
import { getDictionary } from "@/i18n/dictionaries";
import { LanguageProvider } from "@/providers/LanguageProvider";
import { Noto_Sans, Noto_Sans_Mono } from "next/font/google";

export const metadata: Metadata = {
  title: "Flower Shop",
  manifest: "/manifest.json",
};

const geistSans = Noto_Sans({
  variable: "--font-geist-sans",
  subsets: ["latin", "cyrillic"],
});

const geistMono = Noto_Sans_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin", "cyrillic"],
});

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const dictionary = await getDictionary("en");

  return (
    <html lang="ru" dir="ltr">
      <body className={`${geistSans.variable} ${geistMono.variable} ${geistSans.className} antialiased !min-h-screen flex flex-col`}>
        <ContextProviderLayout>
          <LanguageProvider dictionary={dictionary} lang="en">
            {children}
          </LanguageProvider>
        </ContextProviderLayout>
      </body>
    </html>
  );
}
