"use client";

export default function OfficerManagementPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <h1 className="text-2xl font-bold mb-2">Officer Management</h1>
      <p className="text-gray-400 mb-8">
        Manage officer records, integrity scores, batch assignments, and disciplinary actions.
      </p>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total Officers", value: "0", color: "text-blue-400" },
          { label: "Active", value: "0", color: "text-green-400" },
          { label: "Under Review", value: "0", color: "text-amber-400" },
          { label: "Avg Integrity Score", value: "N/A", color: "text-purple-400" },
        ].map((s) => (
          <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-sm text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-6 py-3 text-sm text-gray-400">Badge #</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Name</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Department</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Integrity Score</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Active Cases</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} className="text-center py-12 text-gray-500">
                Connect to accountability service to load officer data
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h3 className="font-medium mb-2">Fine Structure for Misconduct</h3>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div><span className="text-yellow-400">Minor:</span> Up to Rs. 3,000</div>
          <div><span className="text-orange-400">Moderate:</span> Up to Rs. 50,000</div>
          <div><span className="text-red-400">Severe:</span> Up to Rs. 1,00,000</div>
          <div><span className="text-red-600">Extreme:</span> Rs. 2,00,000+</div>
        </div>
      </div>
    </div>
  );
}
