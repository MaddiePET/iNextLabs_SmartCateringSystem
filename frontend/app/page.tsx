"use client";

import { useState } from "react";

export default function Home() {
  const [userRequest, setUserRequest] = useState(
    "Wedding dinner for 50 pax, RM120 per head, halal chicken and vegetarian menu"
  );
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function generatePlan() {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_request: userRequest }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate catering plan");
      }

      const data = await res.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      alert("Backend is still processing or unavailable. Make sure FastAPI is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold">
          Smart Catering Multi-Agent System
        </h1>

        <textarea
          className="w-full min-h-32 rounded-xl p-4 text-black"
          value={userRequest}
          onChange={(e) => setUserRequest(e.target.value)}
        />

        <button
          onClick={generatePlan}
          disabled={loading}
          className="rounded-xl bg-blue-500 px-6 py-3 font-semibold disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Catering Plan"}
        </button>

        {result && (
          <div className="grid gap-4">
            <Card title="Menu Design" content={result.menu} />
            <Card title="Inventory & Procurement" content={result.inventory_report} />
            <Card title="Compliance" content={result.compliance_report} />
            <Card title="Logistics" content={result.logistics_timeline} />
            <Card title="Risk Audit" content={result.risk_assessment} />
            <Card title="Final Quote" content={result.pricing_breakdown} />
            <Card title="Client Feedback" content={result.client_feedback} />
          </div>
        )}
      </div>
    </main>
  );
}

function Card({ title, content }: { title: string; content: string }) {
  return (
    <section className="rounded-2xl bg-slate-900 border border-slate-700 p-5">
      <h2 className="text-xl font-bold mb-3">{title}</h2>
      <pre className="whitespace-pre-wrap text-sm text-slate-200">{content}</pre>
    </section>
  );
}