import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI PoliceNet - Police Dashboard",
  description: "FIR management, investigations, evidence review, and officer tools",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
