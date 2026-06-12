"use client";

export default function AuditPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <h1 className="text-2xl font-bold mb-2">Audit Controls</h1>
      <p className="text-gray-400 mb-8">All actions are logged in an append-only audit trail. Records cannot be deleted or modified.</p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-2xl font-bold text-blue-400">0</p>
          <p className="text-sm text-gray-500">Total Audit Entries</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-2xl font-bold text-amber-400">0</p>
          <p className="text-sm text-gray-500">Suspicious Activities</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-2xl font-bold text-green-400">0</p>
          <p className="text-sm text-gray-500">Compliance Score</p>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="px-6 py-4 border-b border-gray-800">
          <h3 className="font-medium">Recent Activity Logs</h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-6 py-3 text-sm text-gray-400">Timestamp</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">User</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Action</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">Resource</th>
              <th className="text-left px-6 py-3 text-sm text-gray-400">IP Address</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={5} className="text-center py-12 text-gray-500">
                Connect to audit service to load logs
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
