import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./styles.css";

export const metadata: Metadata = {
  title: "Aeropex Buyer Intelligence Platform",
  description: "Aeropex internal control panel shell",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
