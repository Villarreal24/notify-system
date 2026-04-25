import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppChakraProvider } from "@/components/chakra-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Notification System",
  description: "Route category-based notifications across user channels.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <AppChakraProvider>{children}</AppChakraProvider>
      </body>
    </html>
  );
}
