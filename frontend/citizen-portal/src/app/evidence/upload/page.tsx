"use client";

import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";

export default function UploadEvidencePage() {
  const [formData, setFormData] = useState({
    firId: "",
    fileType: "video",
    description: "",
  });
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ evidenceId: string; status: string; reviewDeadline: string } | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/v1"}/evidence/upload`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          firId: formData.firId,
          fileType: formData.fileType,
          fileFormat: file?.type || "unknown",
          fileSizeBytes: file?.size || 0,
          metadata: { captureDate: new Date().toISOString() },
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || "Upload failed");

      setResult(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Evidence</h1>
        <p className="text-gray-500 mb-8">Evidence is hashed (SHA-256), verified by AI, and registered on blockchain for tamper-proof custody.</p>

        {result && (
          <div className="bg-success-500/10 text-success-600 p-4 rounded-lg mb-6">
            <p className="font-medium">Evidence uploaded successfully!</p>
            <p className="text-sm mt-1">Evidence ID: {result.evidenceId}</p>
            <p className="text-sm">Status: Temporary &mdash; Review deadline: {new Date(result.reviewDeadline).toLocaleDateString()}</p>
            <p className="text-sm mt-2 text-amber-600">You have 5 days to upload complete evidence. Upload 3+ recordings of the same event for automatic permanent verification.</p>
          </div>
        )}

        {error && (
          <div className="bg-danger-500/10 text-danger-500 px-4 py-3 rounded-lg mb-6">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="card max-w-2xl space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">FIR / Complaint ID *</label>
            <input type="text" value={formData.firId} onChange={(e) => setFormData({ ...formData, firId: e.target.value })} className="input-field" placeholder="Enter FIR ID" required />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Evidence Type</label>
            <select value={formData.fileType} onChange={(e) => setFormData({ ...formData, fileType: e.target.value })} className="input-field">
              <option value="video">Video (MP4, AVI, MOV, WebM)</option>
              <option value="audio">Audio (MP3, WAV, OGG, M4A)</option>
              <option value="image">Image (JPEG, PNG, BMP, TIFF)</option>
              <option value="document">Document (PDF, DOCX)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Upload File *</label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="input-field"
              accept={formData.fileType === "video" ? "video/*" : formData.fileType === "audio" ? "audio/*" : formData.fileType === "image" ? "image/*" : ".pdf,.docx"}
              required
            />
            <p className="text-xs text-gray-400 mt-1">Max file size: 500MB</p>
          </div>

          <div className="bg-amber-50 p-4 rounded-lg text-sm text-amber-700">
            <strong>Evidence Workflow:</strong>
            <ul className="mt-2 space-y-1 list-disc list-inside">
              <li>Uploaded evidence is initially marked as &ldquo;Temporary Review Evidence&rdquo;</li>
              <li>You have 3-5 days to upload complete evidence</li>
              <li>Moderators + AI will verify authenticity</li>
              <li>3+ uploads of the same event auto-promote to &ldquo;Permanent Evidence&rdquo;</li>
              <li>Verified evidence can be used in court proceedings</li>
            </ul>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Uploading..." : "Upload Evidence"}
          </button>
        </form>
      </main>
    </div>
  );
}
