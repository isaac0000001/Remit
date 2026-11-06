import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "REMIT | International Money Transfers",
  description:
    "A smarter way to manage international money transfers and payments.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
