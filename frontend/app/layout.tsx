import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SentinelAI",
  description: "Multi-layer security, compliance, and trust management for autonomous AI agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="pl-[76px] md:pl-[152px]">
          <div className="mx-auto max-w-6xl px-5 md:px-8 py-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
