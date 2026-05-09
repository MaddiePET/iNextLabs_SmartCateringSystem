"use client";

import { useState } from "react";

type CateringPlan = {
  menu: string;
  inventory_report: string;
  compliance_report: string;
  logistics_timeline: string;
  risk_assessment: string;
  pricing_breakdown: string;
  client_feedback: string;
};

const loadingSteps = [
  "Running Receptionist Agent...",
  "Retrieving supplier knowledge...",
  "Planning menu...",
  "Checking inventory...",
  "Checking compliance...",
  "Planning logistics...",
  "Auditing risks...",
  "Optimizing pricing...",
  "Reviewing client feedback...",
  "Saving to Azure Blob...",
];

export default function Home() {
  const [form, setForm] = useState({
    eventType: "Wedding dinner",
    guestCount: "50",
    budgetPerHead: "120",
    dietaryNeeds: "Halal chicken and vegetarian",
    theme: "Elegant Malaysian fusion",
    eventDate: "2026-05-20",
    location: "Kuala Lumpur",
    notes: "Prefer eco-friendly packaging",
  });

  function buildUserRequest() {
    return `
  Event type: ${form.eventType}
  Guest count: ${form.guestCount} pax
  Budget: RM${form.budgetPerHead} per head
  Dietary needs: ${form.dietaryNeeds}
  Theme: ${form.theme}
  Event date: ${form.eventDate}
  Location: ${form.location}
  Special notes: ${form.notes}
  `;
  }
  const [result, setResult] = useState<CateringPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState("");

  async function generatePlan() {
  setLoading(true);
  setResult(null);
  setError("");
  setStepIndex(0);

  const requestText = buildUserRequest();

  const url = `${
    process.env.NEXT_PUBLIC_API_URL
  }/generate-plan-stream?user_request=${encodeURIComponent(requestText)}`;

  const eventSource = new EventSource(url);

  eventSource.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    const step = data.step;

    const index = loadingSteps.findIndex((s) => s === step);
    if (index !== -1) {
      setStepIndex(index);
    }
  });

  eventSource.addEventListener("complete", (event) => {
    const data = JSON.parse(event.data);
    setResult(data);
    setLoading(false);
    eventSource.close();
  });

  eventSource.addEventListener("error", (event) => {
    console.error(event);
    setError("Streaming failed. Make sure FastAPI is running.");
    setLoading(false);
    eventSource.close();
  });
}

  return (
    <main className="min-h-screen bg-slate-950 text-white p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
          <p className="text-sm uppercase tracking-widest text-blue-400">
            AI-Powered Multi-Agent System
          </p>

          <h1 className="mt-3 text-4xl font-bold">
            Smart Catering Operations Planner
          </h1>

          <p className="mt-3 text-slate-300">
            Generate menu, inventory, logistics, compliance, pricing, and risk
            insights using coordinated AI agents.
          </p>

          <Input label="Event Type" value={form.eventType} onChange={(v) => setForm({ ...form, eventType: v })} />
          <Input label="Guest Count" value={form.guestCount} onChange={(v) => setForm({ ...form, guestCount: v })} />
          <Input label="Budget Per Head (RM)" value={form.budgetPerHead} onChange={(v) => setForm({ ...form, budgetPerHead: v })} />
          <Input label="Dietary Needs" value={form.dietaryNeeds} onChange={(v) => setForm({ ...form, dietaryNeeds: v })} />
          <Input label="Theme" value={form.theme} onChange={(v) => setForm({ ...form, theme: v })} />
          <Input label="Event Date" value={form.eventDate} onChange={(v) => setForm({ ...form, eventDate: v })} />
          <Input label="Location" value={form.location} onChange={(v) => setForm({ ...form, location: v })} />
          <Input label="Special Notes" value={form.notes} onChange={(v) => setForm({ ...form, notes: v })} />

          <button
            onClick={generatePlan}
            disabled={loading}
            className="mt-4 rounded-2xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Generating..." : "Generate Catering Plan"}
          </button>
        </section>

        {loading && (
          <section className="rounded-3xl border border-blue-800 bg-blue-950/40 p-6">
            <h2 className="text-xl font-bold">Agent Workflow Running</h2>
            <p className="mt-2 text-blue-200">{loadingSteps[stepIndex]}</p>

            <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{
                  width: `${((stepIndex + 1) / loadingSteps.length) * 100}%`,
                }}
              />
            </div>
          </section>
        )}

        {error && (
          <section className="rounded-2xl border border-red-800 bg-red-950 p-4 text-red-200">
            {error}
          </section>
        )}

        {result && (
          <section className="grid gap-5 md:grid-cols-2">
            <ResultCard title="Menu Design" content={result.menu} />
            <ResultCard
              title="Inventory & Procurement"
              content={result.inventory_report}
            />
            <ResultCard title="Compliance" content={result.compliance_report} />
            <ResultCard title="Logistics" content={result.logistics_timeline} />
            <ResultCard title="Risk Audit" content={result.risk_assessment} />
            <ResultCard title="Final Quote" content={result.pricing_breakdown} />
            <ResultCard
              title="Client Feedback"
              content={result.client_feedback}
              wide
            />
          </section>
        )}
      </div>
    </main>
  );
}

function ResultCard({
  title,
  content,
  wide = false,
}: {
  title: string;
  content: string;
  wide?: boolean;
}) {
  return (
    <article
      className={`rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg ${
        wide ? "md:col-span-2" : ""
      }`}
    >
      <h2 className="mb-4 text-2xl font-bold text-blue-300">{title}</h2>
      <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-200">
        {content || "No output generated."}
      </pre>
    </article>
  );
}

function Input({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-blue-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}