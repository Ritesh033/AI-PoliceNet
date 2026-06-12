"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";

interface DashboardStats {
  totalComplaints: number;
  activeInvestigations: number;
  evidenceUploaded: number;
  resolvedCases: number;
}

export default function DashboardPage() {
  const [user, setUser] = useState<{ fullName: string; registrationId: string } | null>(null);
  const [stats] = useState<DashboardStats>({
    totalComplaints: 0,
    activeInvestigations: 0,
    evidenceUploaded: 0,
    resolvedCases: 0,
  });

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch { /* ignore */ }
    }
  }, []);

  const statCards = [
    { label: "Total Complaints", value: stats.totalComplaints, color: "bg-blue-500" },
    { label: "Active Investigations", value: stats.activeInvestigations, color: "bg-amber-500" },
    { label: "Evidence Uploaded", value: stats.evidenceUploaded, color: "bg-emerald-500" },
    { label: "Resolved Cases", value: stats.resolvedCases, color: "bg-purple-500" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome{user ? `, ${user.fullName}` : ""}
          </h1>
          {user && (
            <p className="text-sm text-gray-500 mt-1">Registration ID: {user.registrationId}</p>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat) => (
            <div key={stat.label} className="card">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                  <span className="text-white font-bold text-lg">{stat.value}</span>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                  <p className="text-sm text-gray-500">{stat.label}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link href="/complaints/new" className="card hover:shadow-md transition-shadow group">
            <h3 className="font-semibold text-gray-900 group-hover:text-primary-500">File a Complaint</h3>
            <p className="text-sm text-gray-500 mt-1">Submit a new complaint with AI-assisted categorization</p>
          </Link>
          <Link href="/evidence/upload" className="card hover:shadow-md transition-shadow group">
            <h3 className="font-semibold text-gray-900 group-hover:text-primary-500">Upload Evidence</h3>
            <p className="text-sm text-gray-500 mt-1">Upload video, audio, images, or documents securely</p>
          </Link>
          <Link href="/emergency" className="card hover:shadow-md transition-shadow group border-danger-500/20">
            <h3 className="font-semibold text-danger-500">Emergency Report</h3>
            <p className="text-sm text-gray-500 mt-1">Urgent reporting for immediate law enforcement response</p>
          </Link>
        </div>
      </main>
    </div>
  );
}
