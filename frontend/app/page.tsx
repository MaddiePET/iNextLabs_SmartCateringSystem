"use client";

import { useState } from "react";

type CateringPlan = {
  plan_id: string;
  event_details: string;
  guest_count: number;
  budget_per_head: number;
  menu: string;
  inventory_report: string;
  compliance_report: string;
  logistics_timeline: string;
  risk_assessment: string;
  pricing_breakdown: string;
  client_feedback: string;
  system_validation: string;
};

const loadingSteps = [
  "Running Receptionist Agent...",
  "Loading knowledge Azure AI Search...",
  "Planning menu...",
  "Checking inventory...",
  "Checking compliance...",
  "Planning logistics...",
  "Auditing risks...",
  "Optimizing pricing...",
  "Reviewing proposal...",
  "Saving plan to Azure Blob...",
];

const dietaryOptions = [
  "None",
  "Halal",
  "Vegetarian",
  "Vegan",
  "Dairy-Free",
  "Gluten-Free",
  "Nut Allergy",
  "Seafood Allergy",
  "Egg-Free",
];

export default function Home() {
  const [form, setForm] = useState({
    eventType: "",
    guestCount: "",
    budgetPerHead: "",
    dietaryNeeds: "",
    theme: "",
    eventDate: "",
    location: "",
    notes: "",
  });

  const [feedback, setFeedback] = useState({
    name: "",
    rating: "",
    comment: "",
  });

  async function submitFeedback() {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/submit-feedback`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...feedback,
            plan_id: result?.plan_id,
          }),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to submit feedback");
      }

      const data = await res.json();

      setSuccessMessage(
        `Feedback received successfully and saved as ${data.blob}`
      );

      setFeedbackSubmitted(true);

      setFeedback({
        name: "",
        rating: "",
        comment: "",
      });

    } catch (err) {
      console.error(err);
      alert("Failed to submit feedback.");
    }
  }

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
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

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
            iNextLabs Smart Catering Operations Planner
          </h1>

          <p className="mt-3 text-slate-300">
            Generate menu, inventory, logistics, compliance, pricing, and risk
            insights using coordinated AI agents.
          </p>

          <Input
            label="Event Type"
            placeholder="e.g. Wedding Dinner"
            value={form.eventType}
            onChange={(v) => setForm({ ...form, eventType: v })}
          />

          <Input
            label="Guest Count"
            placeholder="e.g. 150"
            value={form.guestCount}
            onChange={(v) => setForm({ ...form, guestCount: v })}
          />

          <Input
            label="Budget Per Head (RM)"
            placeholder="e.g. 120"
            value={form.budgetPerHead}
            onChange={(v) => setForm({ ...form, budgetPerHead: v })}
          />

          <div className="space-y-3">
            <span className="text-sm font-medium text-slate-300">
              Dietary Needs & Allergies
            </span>

            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              {dietaryOptions.map((option) => {
                const selected = form.dietaryNeeds
                  .split(",")
                  .map((x) => x.trim())
                  .includes(option);

                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => {
                      const current = form.dietaryNeeds
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean);

                      let updated;

                      if (selected) {
                        updated = current.filter((x) => x !== option);
                      } else {
                        updated = [...current, option];
                      }

                      setForm({
                        ...form,
                        dietaryNeeds: updated.join(", "),
                      });
                    }}
                    className={`rounded-xl border p-3 text-sm transition ${
                      selected
                        ? "border-blue-500 bg-blue-600 text-white"
                        : "border-slate-700 bg-slate-950 text-slate-300 hover:border-blue-500"
                    }`}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          </div>

          <Input
            label="Theme"
            placeholder="e.g. Japanese Fusion"
            value={form.theme}
            onChange={(v) => setForm({ ...form, theme: v })}
          />

          <Input
            label="Event Date"
            placeholder="e.g. 2026-05-20"
            value={form.eventDate}
            onChange={(v) => setForm({ ...form, eventDate: v })}
          />

          <Input
            label="Location"
            placeholder="e.g. Kuala Lumpur"
            value={form.location}
            onChange={(v) => setForm({ ...form, location: v })}
          />

          <Input
            label="Special Notes"
            placeholder="e.g. Prefer eco-friendly packaging"
            value={form.notes}
            onChange={(v) => setForm({ ...form, notes: v })}
          />
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
            <ResultCard title="Final System Validation" content={result.system_validation} />
            <ResultCard title="Risk Audit" content={result.risk_assessment} />
            <ResultCard title="Final Quote" content={result.pricing_breakdown} />
            <ResultCard title="Client Feedback" content={result.client_feedback} wide />
          </section>
        )}

        {successMessage && (
          <section className="rounded-2xl border border-green-700 bg-green-950 p-4 text-green-200">
            ✅ {successMessage}
          </section>
        )}

        {result && !feedbackSubmitted && (
          <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-2xl font-bold text-blue-300">
              Customer Feedback
            </h2>

            <div className="mt-4 space-y-4">
              <Input
                label="Customer Name"
                value={feedback.name}
                onChange={(v) => setFeedback({ ...feedback, name: v })}
                placeholder="e.g. Sarah"
              />

              <Input
                label="Rating (1-5)"
                value={feedback.rating}
                onChange={(v) => setFeedback({ ...feedback, rating: v })}
                placeholder="e.g. 4"
              />

              <label className="space-y-2 block">
                <span className="text-sm font-medium text-slate-300">
                  Comments
                </span>

                <textarea
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white"
                  rows={5}
                  placeholder="Enter customer feedback..."
                  value={feedback.comment}
                  onChange={(e) =>
                    setFeedback({
                      ...feedback,
                      comment: e.target.value,
                    })
                  }
                />
              </label>

              <button
                onClick={submitFeedback}
                className="rounded-2xl bg-green-600 px-6 py-3 font-semibold hover:bg-green-500"
              >
                Submit Feedback
              </button>
            </div>
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
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-blue-500"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
