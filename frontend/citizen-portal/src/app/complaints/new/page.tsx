"use client";

import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";

export default function NewComplaintPage() {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    category: "",
    severity: "medium",
    incidentDate: "",
    incidentLocation: "",
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState("");

  function updateField(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(null);

    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/v1"}/citizens/complaints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || "Failed to file complaint");

      setSuccess(`Complaint filed successfully! FIR Number: ${data.data.fir_number}`);
      setFormData({ title: "", description: "", category: "", severity: "medium", incidentDate: "", incidentLocation: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to file complaint");
    } finally {
      setLoading(false);
    }
  }

  const categories = [
    "Theft / Robbery", "Assault / Violence", "Fraud / Cheating",
    "Cybercrime", "Domestic Violence", "Corruption / Bribery",
    "Police Misconduct", "Harassment", "Missing Person",
    "Traffic Violation", "Public Nuisance", "Other",
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">File a Complaint</h1>
        <p className="text-gray-500 mb-8">Your complaint will be registered as an FIR with a unique tracking ID. AI will assist with categorization and priority scoring.</p>

        {success && (
          <div className="bg-success-500/10 text-success-600 px-4 py-3 rounded-lg mb-6">{success}</div>
        )}
        {error && (
          <div className="bg-danger-500/10 text-danger-500 px-4 py-3 rounded-lg mb-6">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="card max-w-2xl space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Complaint Title *</label>
            <input type="text" value={formData.title} onChange={(e) => updateField("title", e.target.value)} className="input-field" placeholder="Brief title of the incident" required minLength={5} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select value={formData.category} onChange={(e) => updateField("category", e.target.value)} className="input-field">
              <option value="">Select a category</option>
              {categories.map((cat) => (
                <option key={cat} value={cat.toLowerCase().replace(/\s+\/?\s*/g, "_")}>{cat}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
            <select value={formData.severity} onChange={(e) => updateField("severity", e.target.value)} className="input-field">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical - Immediate Attention Required</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Detailed Description *</label>
            <textarea
              value={formData.description} onChange={(e) => updateField("description", e.target.value)}
              className="input-field min-h-[150px]" placeholder="Describe the incident in detail..."
              required minLength={20}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Incident Date</label>
              <input type="datetime-local" value={formData.incidentDate} onChange={(e) => updateField("incidentDate", e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Incident Location</label>
              <input type="text" value={formData.incidentLocation} onChange={(e) => updateField("incidentLocation", e.target.value)} className="input-field" placeholder="Address or landmark" />
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg text-sm text-blue-700">
            <strong>Note:</strong> Your complaint will be registered as a tamper-proof FIR. It cannot be modified by any officer without a court order.
            After filing, you will have 3-5 days to upload supporting evidence.
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Filing complaint..." : "File Complaint"}
          </button>
        </form>
      </main>
    </div>
  );
}
