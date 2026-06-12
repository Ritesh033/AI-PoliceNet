import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI PoliceNet - Admin Panel",
  description: "User management, role management, audit controls, and system monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
