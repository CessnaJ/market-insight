import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Insight Dashboard",
  description: "Personal Investment Intelligence System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
