"use client";

import { useState } from "react";

export default function EmergencyPage() {
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleEmergency(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      // TODO: Call emergency notification endpoint
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-red-50">
        <div className="card max-w-md text-center">
          <div className="w-16 h-16 bg-danger-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-2xl font-bold">!</span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Emergency Alert Sent</h2>
          <p className="text-gray-500">Nearby officers have been notified. Stay safe and wait for response.</p>
          <p className="text-sm text-gray-400 mt-4">If in immediate danger, call 112 (India Emergency)</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-red-50 px-4">
      <div className="card max-w-md w-full">
        <div className="text-center mb-6">
          <div className="w-14 h-14 bg-danger-500 rounded-full flex items-center justify-center mx-auto mb-3">
            <span className="text-white text-2xl font-bold">!</span>
          </div>
          <h1 className="text-2xl font-bold text-danger-500">Emergency Report</h1>
          <p className="text-sm text-gray-500 mt-1">For immediate threats to life or safety</p>
        </div>

        <div className="bg-danger-500/10 p-3 rounded-lg mb-6 text-sm text-danger-600 text-center">
          If in immediate danger, call <strong>112</strong> (India Emergency)
        </div>

        <form onSubmit={handleEmergency} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">What is happening? *</label>
            <textarea
              value={description} onChange={(e) => setDescription(e.target.value)}
              className="input-field min-h-[100px]" placeholder="Describe the emergency..."
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Location</label>
            <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} className="input-field" placeholder="Address or landmark" />
          </div>
          <button type="submit" className="btn-danger w-full !py-3 text-lg" disabled={loading}>
            {loading ? "Sending alert..." : "Send Emergency Alert"}
          </button>
        </form>
      </div>
    </div>
  );
}
