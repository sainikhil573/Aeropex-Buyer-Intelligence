import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Aeropex Buyer Intelligence Platform",
  description: "Aeropex internal control panel shell",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
