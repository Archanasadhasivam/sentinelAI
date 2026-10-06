"use client";

/** Wraps every page: login gate + side Nav. The login and sign-up pages get
 * a plain centred layout with no Nav. */
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AuthProvider } from "@/components/AuthProvider";
import { Nav } from "@/components/Nav";
import { PUBLIC_PAGES } from "@/lib/api";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PAGES.includes(pathname);

  return (
    <AuthProvider>
      {isPublic ? (
        <main className="min-h-screen flex items-center justify-center px-5 py-10">{children}</main>
      ) : (
        <>
          <Nav />
          <main className="pl-[76px] md:pl-[152px]">
            <div className="mx-auto max-w-6xl px-5 md:px-8 py-8">{children}</div>
          </main>
        </>
      )}
    </AuthProvider>
  );
}