import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI PoliceNet - Citizen Portal",
  description: "Transparent Policing, Trusted Justice - File complaints, upload evidence, track cases",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
