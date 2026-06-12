"use client";

import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">AP</span>
          </div>
          <h1 className="text-white text-xl font-bold">AI PoliceNet</h1>
        </div>
        <div className="flex gap-4">
          <Link href="/auth/login" className="btn-secondary !bg-transparent !text-white !border-white/30 hover:!bg-white/10">
            Login
          </Link>
          <Link href="/auth/register" className="btn-primary !bg-accent-500 hover:!bg-accent-600">
            Register
          </Link>
        </div>
      </header>

      {/* Hero */}
      <main className="max-w-6xl mx-auto px-8 py-20">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold text-white mb-6">
            Transparent Policing,<br />Trusted Justice
          </h2>
          <p className="text-xl text-blue-200 max-w-2xl mx-auto mb-10">
            AI-powered citizen protection platform. File complaints securely, upload evidence with
            tamper-proof verification, and track your case in real-time.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/register" className="btn-primary !bg-accent-500 hover:!bg-accent-600 !px-8 !py-3 text-lg">
              Get Started
            </Link>
            <Link href="/emergency" className="btn-danger !px-8 !py-3 text-lg">
              Emergency Report
            </Link>
          </div>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          {[
            {
              title: "File Complaints",
              desc: "Submit complaints securely with AI-assisted categorization and priority scoring.",
              icon: "FIR",
            },
            {
              title: "Upload Evidence",
              desc: "SHA-256 hashed, blockchain-verified evidence with chain-of-custody tracking.",
              icon: "EVD",
            },
            {
              title: "Track Cases",
              desc: "Real-time case tracking with full audit trail. Tamper-proof FIR records.",
              icon: "TRK",
            },
            {
              title: "Officer Accountability",
              desc: "Report misconduct. Officers face fines for false FIRs and abuse of power.",
              icon: "ACC",
            },
            {
              title: "AI Analysis",
              desc: "AI validates complaints, detects false reports, and scores case priority.",
              icon: "AI",
            },
            {
              title: "Court Integration",
              desc: "Digital case files, verified evidence, and court order management.",
              icon: "CRT",
            },
          ].map((feature) => (
            <div key={feature.title} className="card !bg-white/10 !border-white/10 backdrop-blur-sm">
              <div className="w-12 h-12 bg-accent-500/20 rounded-lg flex items-center justify-center mb-4">
                <span className="text-accent-500 font-bold text-sm">{feature.icon}</span>
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{feature.title}</h3>
              <p className="text-blue-200 text-sm">{feature.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-8 text-blue-300 text-sm">
        <p>AI PoliceNet &mdash; AI assists decisions, humans make final legal determinations.</p>
      </footer>
    </div>
  );
}
