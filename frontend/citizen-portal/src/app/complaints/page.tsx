"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";

interface Complaint {
  id: string;
  fir_number: string;
  title: string;
  status: string;
  severity: string;
  category: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  registered: "bg-blue-100 text-blue-700",
  under_review: "bg-amber-100 text-amber-700",
  investigation: "bg-purple-100 text-purple-700",
  court_referred: "bg-indigo-100 text-indigo-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-700",
  false_report: "bg-red-100 text-red-700",
};

export default function ComplaintsPage() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem("accessToken");
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/v1"}/citizens/complaints`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setComplaints(data.data || []);
      } catch {
        // Handle error
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-gray-900">My Complaints</h1>
          <Link href="/complaints/new" className="btn-primary">File New Complaint</Link>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : complaints.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-500 mb-4">No complaints filed yet</p>
            <Link href="/complaints/new" className="btn-primary">File your first complaint</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {complaints.map((c) => (
              <div key={c.id} className="card flex items-center justify-between hover:shadow-md transition-shadow">
                <div>
                  <p className="text-xs text-gray-400 mb-1">{c.fir_number}</p>
                  <h3 className="font-medium text-gray-900">{c.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Filed on {new Date(c.created_at).toLocaleDateString()}
                    {c.category && ` \u2022 ${c.category}`}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`status-badge ${statusColors[c.status] || "bg-gray-100 text-gray-700"}`}>
                    {c.status?.replace(/_/g, " ")}
                  </span>
                  <Link href={`/complaints/${c.id}`} className="text-primary-500 text-sm hover:underline">View</Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
