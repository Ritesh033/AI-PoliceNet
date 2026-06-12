"use client";

import { useState } from "react";

export default function EvidenceReviewPage() {
  const [filter, setFilter] = useState("temporary");
  const filters = ["temporary", "under_review", "verified_permanent", "rejected"];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-2xl font-bold mb-2">Evidence Review</h1>
      <p className="text-gray-400 mb-6">Review uploaded evidence. Verify authenticity and promote to permanent status.</p>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm ${filter === f ? "bg-blue-600" : "bg-gray-800 hover:bg-gray-700"}`}
          >
            {f.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <div className="grid gap-4">
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 text-center text-gray-500">
          Connect to evidence service to load review queue
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
          <p className="text-3xl font-bold text-amber-400">0</p>
          <p className="text-sm text-gray-400">Pending Review</p>
        </div>
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
          <p className="text-3xl font-bold text-green-400">0</p>
          <p className="text-sm text-gray-400">Verified Today</p>
        </div>
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
          <p className="text-3xl font-bold text-red-400">0</p>
          <p className="text-sm text-gray-400">Rejected Today</p>
        </div>
      </div>
    </div>
  );
}
