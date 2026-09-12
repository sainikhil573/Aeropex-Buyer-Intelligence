"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { label: "Overview", href: "/" },
  { label: "Agents", href: "/agents" },
  { label: "Buyer Intelligence", href: "/buyer-intelligence" },
  { label: "Suppliers", href: "/suppliers" },
  { label: "Sources", href: "/sources" },
  { label: "Approvals", href: "/approvals" },
  { label: "Data Pipeline", href: "/data-pipeline" },
  { label: "System Health", href: "/system-health" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span>Aeropex</span>
          <small>Control Panel</small>
        </div>
        <nav>
          {navItems.map((item) => {
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link aria-current={isActive ? "page" : undefined} href={item.href} key={item.href}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <section className="content">{children}</section>
    </main>
  );
}
