import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MaRe Studio",
  description:
    "Luxury-standard content generation for MaRe Head Spa — brand-aligned scripts, prompts, and rendered frames.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
