"use client";

import { useState } from "react";

export default function FirManagementPage() {
  const [filter, setFilter] = useState("all");

  const statusFilters = ["all", "registered", "under_review", "investigation", "court_referred", "resolved", "closed"];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-2xl font-bold mb-6">FIR Management</h1>

      <div className="flex gap-2 mb-6">
        {statusFilters.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-4 py-2 rounded-lg text-sm ${filter === s ? "bg-blue-600" : "bg-gray-800 hover:bg-gray-700"}`}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left px-6 py-3 text-sm text-gray-400">FIR Number</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Title</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Status</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Priority</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Date</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} className="text-center py-12 text-gray-500">
                Connect to FIR service to load data
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-6 bg-gray-800 rounded-xl border border-gray-700 p-4 text-sm text-amber-400">
        <strong>Tamper-Proof Notice:</strong> FIR records are immutable. Status changes are recorded in the audit trail.
        Amendments require court authorization.
      </div>
    </div>
  );
}
