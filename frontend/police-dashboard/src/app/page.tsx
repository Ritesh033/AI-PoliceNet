"use client";

import Link from "next/link";

export default function PoliceDashboard() {
  const modules = [
    { href: "/fir-management", title: "FIR Management", desc: "View, assign, and track FIRs", count: 0 },
    { href: "/investigations", title: "Investigation Center", desc: "Manage active investigations and timelines", count: 0 },
    { href: "/evidence-review", title: "Evidence Review", desc: "Review and verify uploaded evidence", count: 0 },
    { href: "/accountability", title: "Officer Records", desc: "Integrity scores, reviews, and disciplinary records", count: 0 },
    { href: "/alerts", title: "Alerts & Notifications", desc: "Emergency alerts and case notifications", count: 0 },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="font-bold">PD</span>
          </div>
          <div>
            <h1 className="font-bold text-lg">AI PoliceNet</h1>
            <p className="text-xs text-gray-400">Police Dashboard</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-8">
        <h2 className="text-2xl font-bold mb-8">Dashboard Overview</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="bg-gray-800 border border-gray-700 rounded-xl p-6 hover:border-blue-500 transition-colors"
            >
              <h3 className="font-semibold text-lg mb-2">{m.title}</h3>
              <p className="text-sm text-gray-400">{m.desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
