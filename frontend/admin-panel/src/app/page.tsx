"use client";

import Link from "next/link";

export default function AdminDashboard() {
  const modules = [
    { href: "/users", title: "User Management", desc: "Manage citizen, officer, and admin accounts" },
    { href: "/officers", title: "Officer Management", desc: "Integrity scores, batch numbers, postings" },
    { href: "/roles", title: "Role Management", desc: "Define roles and permissions" },
    { href: "/audit", title: "Audit Controls", desc: "View access logs and activity trails" },
    { href: "/system", title: "System Monitoring", desc: "Service health, performance metrics, alerts" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
            <span className="font-bold">AD</span>
          </div>
          <div>
            <h1 className="font-bold">AI PoliceNet</h1>
            <p className="text-xs text-gray-400">Admin Panel</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-8">
        <h2 className="text-2xl font-bold mb-4">Administration</h2>
        <p className="text-gray-400 mb-8">Manage users, roles, officers, and monitor system health.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((m) => (
            <Link key={m.href} href={m.href} className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-purple-500 transition-colors">
              <h3 className="font-semibold text-lg mb-2">{m.title}</h3>
              <p className="text-sm text-gray-400">{m.desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
