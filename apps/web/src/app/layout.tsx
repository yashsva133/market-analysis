import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "INDIA TERMINAL // Market Intelligence Core",
  description: "Personal-use local-first Indian equity research and event-monitoring terminal",
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
