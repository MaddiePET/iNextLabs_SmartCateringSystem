"use client";

import { useRef, useState } from "react";
import Image from "next/image";

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
  proposal_review: string;
  system_validation: string;
};

const loadingSteps = [
  "Running Receptionist Agent...",
  "Loading knowledge Azure AI Search...",
  "Planning menu...",
  "Checking inventory...",
  "Inventory validation completed...",
  "Checking compliance...",
  "Compliance validation completed...",
  "Planning logistics...",
  "Auditing risks...",
  "Calculating pricing...",
  "Reviewing proposal...",
  "Saving plan to Azure Blob...",
];

const dietaryOptions = [
  "None",
  "Vegetarian",
  "Vegan",
  "Nut Allergy",
  "Dairy Free",
  "Gluten Free"
];

const colorMap = {
  default: "text-blue-300",
  success: "text-green-400",
  warning: "text-yellow-400",
  danger: "text-red-400",
};

function getActiveAgent(step: string) {
  const value = step.toLowerCase();

  if (value.includes("receptionist")) return "Receptionist Agent";
  if (value.includes("knowledge")) return "Knowledge Retrieval Agent";
  if (value.includes("menu") || value.includes("chef")) return "Menu Planning Agent";
  if (value.includes("inventory")) return "Inventory & Procurement Agent";
  if (value.includes("compliance")) return "Compliance Agent";
  if (value.includes("logistics")) return "Logistics Planning Agent";
  if (value.includes("risk") || value.includes("auditing")) return "Monitoring Agent";
  if (value.includes("pricing")) return "Pricing & Optimization Agent";
  if (value.includes("review")) return "Proposal Review Agent";
  if (value.includes("saving")) return "Persistence Agent";

  return "Multi-Agent Orchestrator";
}

const MIN_STEP_DURATION = 500;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getStepIndex(step: string) {
  const value = step.toLowerCase();

  if (value.includes("receptionist")) return 0;
  if (value.includes("knowledge")) return 1;
  if (value.includes("planning menu")) return 2;
  if (value.includes("checking inventory")) return 3;
  if (value.includes("inventory validation") || value.includes("inventory review")) return 4;
  if (value.includes("checking compliance")) return 5;
  if (value.includes("compliance validation") || value.includes("compliance feedback")) return 6;
  if (value.includes("logistics")) return 7;
  if (value.includes("risk") || value.includes("auditing")) return 8;
  if (value.includes("pricing")) return 9;
  if (value.includes("review")) return 10;
  if (value.includes("saving")) return 11;

  return 0;
}

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

  const guestLimits = { min: 20, max: 500 };
  const budgetLimits = { min: 70, max: 500 }; 
  
  const [feedback, setFeedback] = useState({
    name: "",
    rating: "",
    comment: "",
  });

  async function submitFeedback() {
    setFeedbackSaving(true);
    setSuccessMessage("");

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
    } finally {
      setFeedbackSaving(false);
    }
  }

  function buildUserRequest() {
    return [
      `Event: ${form.eventType}`,
      `Guest count: ${form.guestCount} pax`,
      `Budget: RM ${form.budgetPerHead} per head`,
      `Dietary needs: ${form.dietaryNeeds}`,
      `Theme: ${form.theme}`,
      `Date: ${form.eventDate}`,
      `Location: ${form.location}`,
      `Notes: ${form.notes}`
    ].join("\n");
  }
  
  const [result, setResult] = useState<CateringPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [error, setError] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const [progressPercent, setProgressPercent] = useState(0);

  async function generatePlan() {
    if (
      !form.eventType ||
      !form.guestCount ||
      !form.budgetPerHead ||
      !form.theme ||
      !form.eventDate ||
      !form.location
    ) {
      setError("Please complete all required fields before generating a plan.");
      return;
    }
    setLoading(true);
    setResult(null);
    setError("");
    setStepIndex(0);
    setCurrentStep("");
    setProgressPercent(0);

    let completed = false;

    const requestText = buildUserRequest();

    const url = `${
      process.env.NEXT_PUBLIC_API_URL
    }/generate-plan-stream?user_request=${encodeURIComponent(requestText)}`;

    const eventSource = new EventSource(url);

    eventSource.addEventListener("progress", async (event) => {
      const data = JSON.parse(event.data);
      const step = data.step;
      const nextIndex = getStepIndex(step);
      const nextPercent = Math.round(((nextIndex + 1) / loadingSteps.length) * 100);

      await delay(MIN_STEP_DURATION);

      setCurrentStep(step);
      setStepIndex((prev) => Math.max(prev, nextIndex));
      setProgressPercent((prev) => Math.max(prev, nextPercent));
    });

    eventSource.addEventListener("complete", (event) => {
      console.log("SSE COMPLETE RECEIVED");

      completed = true;
      const data = JSON.parse(event.data);

      setResult(data);
      setCurrentStep("Completed");
      setStepIndex(loadingSteps.length - 1);
      setLoading(false);
      setProgressPercent(100);

      eventSource.close();
    });

    eventSource.onerror = () => {
      if (completed) return;

      setError("Streaming failed. Check whether FastAPI is still running.");
      setLoading(false);
      eventSource.close();
    };
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
          <div className="flex items-center gap-3">
            <Image
              src="/icon.png"
              alt="iNextLabs Logo"
              width={40}
              height={40}
              className="rounded-lg"
            />

            <p className="text-sm uppercase tracking-widest text-blue-400">
              AI-Powered Multi-Agent System
            </p>
          </div>

          <h1 className="mt-3 text-4xl font-bold">
            iNextLabs Smart Catering Operations Planner
          </h1>

          <p className="mt-3 text-slate-300">
            Generate menu, inventory, logistics, compliance, pricing, and risk
            insights using coordinated AI agents.
          </p>

          <p className="text-xs text-green-400 mb-2 flex items-center gap-1">
            All food is prepared in 100% Halal-certified kitchens. Licensed bar service is handled separately when requested.
          </p>

          <Input
            label="Event Type"
            placeholder="e.g. Wedding Dinner"
            value={form.eventType}
            disabled={loading}
            onChange={(v) => setForm({ ...form, eventType: v })}
          />

          <Input
            label={`Guest Count (Range: ${guestLimits.min} - ${guestLimits.max} pax)`}
            placeholder="e.g. 150"
            value={form.guestCount}
            disabled={loading}
            onChange={(v) => setForm({ ...form, guestCount: v })}
          />
          {parseInt(form.guestCount) > 500 && (
            <p className="text-xs text-red-400 mt-1">⚠️ Exceeds maximum capacity (500 pax)</p>
          )}
          {parseInt(form.guestCount) > 0 && parseInt(form.guestCount) < 20 && (
            <p className="text-xs text-yellow-400 mt-1">⚠️ Below minimum requirement (20 pax)</p>
          )}

          <Input
            label={`Budget Per Head (RM) - Min: RM ${budgetLimits.min}`}
            placeholder="e.g. 120"
            value={form.budgetPerHead}
            disabled={loading}
            onChange={(v) => setForm({ ...form, budgetPerHead: v })}
          />
          {parseFloat(form.budgetPerHead) > 0 && parseFloat(form.budgetPerHead) < budgetLimits.min && (
            <p className="text-xs text-yellow-400 mt-1">⚠️ Below quality floor (Min RM {budgetLimits.min} recommended)</p>
          )}
          {parseFloat(form.budgetPerHead) > budgetLimits.max && (
            <p className="text-xs text-red-400 mt-1">⚠️ Exceeds standard corporate ceiling (Max RM {budgetLimits.max})</p>
          )}

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

                const noneSelected = form.dietaryNeeds
                  .split(",")
                  .map((x) => x.trim())
                  .includes("None");

                const disabled = noneSelected && option !== "None";

                return (
                  <button
                    key={option}
                    type="button"
                    disabled={disabled}
                    onClick={() => {
                      if (option === "None") {
                        if (noneSelected) {
                          setForm({
                            ...form,
                            dietaryNeeds: "",
                          });
                        } else {
                          setForm({
                            ...form,
                            dietaryNeeds: "None",
                          });
                        }

                        return;
                      }

                      const current = form.dietaryNeeds
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean)
                        .filter((x) => x !== "None");

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
                      disabled
                        ? "cursor-not-allowed border-slate-800 bg-slate-900 text-slate-600 opacity-50"
                        : selected
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

            <label className="space-y-2 block">
              <span className="text-sm font-medium text-slate-300">Theme</span>
              <select 
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-blue-500 transition-all cursor-pointer"
                value={form.theme}
                disabled={loading}
                onChange={(e) => setForm({ ...form, theme: e.target.value })}
            >
              <option value="" disabled>Select a theme...</option>
              <option value="Japanese Fusion">Japanese Fusion</option>
              <option value="Traditional Malay">Traditional Malay</option>
              <option value="Western Corporate">Western Corporate</option>
              <option value="Chinese Fusion">Chinese Fusion</option>
            </select>
          </label>

          <label className="space-y-2 block">
            <span className="text-sm font-medium text-slate-300">
              Event Date
            </span>

            <input
              ref={dateInputRef}
              type="date"
              min={new Date().toISOString().split("T")[0]} 
              className="w-full cursor-pointer rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-blue-500 [color-scheme:dark]"
              value={form.eventDate}
              disabled={loading}
              onClick={() => {
                try {
                  dateInputRef.current?.showPicker();
                } catch (e) {
                  console.log("Native picker triggered");
                }
              }}
              onChange={(e) => setForm({ ...form, eventDate: e.target.value })}
            />
            <p className="text-[10px] text-slate-500">Note: Bookings must be made at least 3 days in advance.</p>
          </label>

          <Input
            label="Location"
            placeholder="e.g. Kuala Lumpur"
            value={form.location}
            disabled={loading}
            onChange={(v) => setForm({ ...form, location: v })}
          />

          <Input
            label="Special Notes"
            placeholder="e.g. Prefer eco-friendly packaging"
            value={form.notes}
            disabled={loading}
            onChange={(v) => setForm({ ...form, notes: v })}
          />

          <div className="mt-4 flex flex-wrap gap-2">
          {[
            "Japanese Vegetarian Wedding",
            "Corporate Western Lunch",
            "Malay Buffet Event",
            "Chinese Engagement Party",
          ].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                if (example === "Japanese Vegetarian Wedding") {
                  setForm({
                    eventType: "Wedding Dinner",
                    guestCount: "100",
                    budgetPerHead: "150",
                    dietaryNeeds: "Vegetarian",
                    theme: "Japanese Fusion",
                    eventDate: form.eventDate,
                    location: "kl",
                    notes: "prefer eco-friendly packaging",
                  });
                }

                if (example === "Corporate Western Lunch") {
                  setForm({
                    eventType: "Corporate Lunch",
                    guestCount: "80",
                    budgetPerHead: "120",
                    dietaryNeeds: "None",
                    theme: "Western Corporate",
                    eventDate: form.eventDate,
                    location: "Kuala Lumpur",
                    notes: "wine service",
                  });
                }

                if (example === "Malay Buffet Event") {
                  setForm({
                    eventType: "Buffet Dinner",
                    guestCount: "150",
                    budgetPerHead: "100",
                    dietaryNeeds: "None",
                    theme: "Traditional Malay",
                    eventDate: form.eventDate,
                    location: "Selangor",
                    notes: "prefer eco-friendly packaging",
                  });
                }

                if (example === "Chinese Engagement Party") {
                  setForm({
                    eventType: "Engagement Dinner",
                    guestCount: "500",
                    budgetPerHead: "150",
                    dietaryNeeds: "None",
                    theme: "Chinese Fusion",
                    eventDate: form.eventDate,
                    location: "Petaling Jaya",
                    notes: "need whiskey and beer service",
                  });
                }
              }}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:border-blue-500 hover:text-white"
            >
              {example}
            </button>
          ))}
        </div>
          <button
            onClick={generatePlan}
            disabled={loading}
            className="mt-4 rounded-2xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Generating..." : "Generate Catering Plan"}
          </button>
        </section>

        {loading && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/95 p-4">
            <section className="w-full max-w-lg rounded-3xl border border-blue-700 bg-slate-900/95 p-8 shadow-[0_0_40px_rgba(59,130,246,0.15)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    Active Agent
                  </p>
                  <h2 className="text-2xl font-bold text-blue-400">
                    {getActiveAgent(currentStep || loadingSteps[stepIndex])}
                  </h2>
                </div>
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
              </div>
              
              <p className="mt-4 text-lg font-medium text-white">
                Current Task: <span className="text-blue-200">{currentStep || loadingSteps[stepIndex]}</span>
              </p>

              <div className="mt-6 space-y-2">
                <div className="flex justify-between text-sm text-slate-400">
                  <span>Overall Progress</span>
                  <span>{progressPercent}%</span>
                </div>
                <div className="h-4 overflow-hidden rounded-full bg-slate-800 border border-slate-700">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all duration-700 ease-out shadow-[0_0_15px_rgba(59,130,246,0.5)]"
                    style={{
                      width: `${progressPercent}%`,
                    }}
                  />
                </div>
              </div>
              
              <p className="mt-6 text-center text-xs text-slate-500 italic">
                Please wait while our specialized agents coordinate your plan...
              </p>
            </section>
          </div>
        )}

        {error && (
          <section className="rounded-2xl border border-red-800 bg-red-950 p-4 text-red-200">
            {error}
          </section>
        )}

        {result && (
          <section className="grid gap-4 md:grid-cols-4">
            <MetricCard
              title="Compliance Confidence"
              value={`${getComplianceConfidence(result.compliance_report)}%`}
            />
            <MetricCard
              title="Inventory Confidence"
              value={`${getInventoryConfidence(result.inventory_report)}%`}
            />
            <MetricCard
              title="Risk Level"
              value={getRiskLevel(result.system_validation)}
              type={
                getRiskLevel(result.system_validation) === "HIGH"
                  ? "danger"
                  : getRiskLevel(result.system_validation) === "MEDIUM"
                  ? "warning"
                  : "success"
              }
            />
            <MetricCard
              title="Budget Status"
              value={
                result.system_validation.toLowerCase().includes("exceeds")
                  ? "Over Budget"
                  : "Within Budget"
              }
            />
          </section>
        )}

        {result && (
          <>
            <ProcurementSummary content={result.inventory_report} />

            <section className="grid gap-5 md:grid-cols-2">
            <ResultCard title="Menu Design" content={result.menu} />
            <ResultCard title="Inventory & Procurement" content={result.inventory_report}/>
            <ResultCard title="Compliance" content={result.compliance_report} />
            <ResultCard title="Logistics" content={result.logistics_timeline} />
            <ResultCard title="Final System Validation" content={result.system_validation} />
            <ResultCard title="Risk Audit" content={result.risk_assessment} />
            <FinalQuoteCard content={result.pricing_breakdown} />
            <ResultCard title="Proposal Quality Review" content={result.proposal_review} />
            </section>
          </>
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

              {feedbackSaving && (
                <p className="text-sm text-blue-300">
                  Saving your feedback...
                </p>
              )}
              <button
                onClick={submitFeedback}
                disabled={feedbackSaving}
                className="rounded-2xl bg-green-600 px-6 py-3 font-semibold hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {feedbackSaving ? "Saving feedback..." : "Submit Feedback"}
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
      className={`flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg transition-all hover:border-slate-700 ${
        wide ? "md:col-span-2" : ""
      }`}
    >
      <details open className="flex h-full flex-col overflow-hidden">
        <summary className="mb-4 cursor-pointer text-xl font-bold text-blue-300">
          {title}
        </summary>

        <div className="h-[330px] overflow-y-auto pr-2 custom-scrollbar">
          <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-300 font-sans">
            {content || "No output generated."}
          </pre>
        </div>
      </details>
    </article>
  );
}

function FinalQuoteCard({ content }: { content: string }) {
  const lines = content.split("\n");

  const tableLines = lines.filter((line) => {
    const trimmed = line.trim();
    return trimmed.startsWith("|") && trimmed.endsWith("|");
  });

  const rows = tableLines
    .filter((line) => !line.includes("---"))
    .map((line) =>
      line
        .split("|")
        .map((cell) => cell.trim())
        .filter((cell) => cell !== "")
    );

  const hasTable = rows.length >= 2;
  const headers = hasTable ? rows[0] : [];
  const bodyRows = hasTable ? rows.slice(1) : [];

  const finalQuote = content.match(/\[FINAL QUOTE\].*/i)?.[0] || "";

  const beforeOptimization = content.split("Budget Optimization Suggestions:")[0];

  const summaryLines = beforeOptimization
    .split("\n")
    .filter(
      (line) =>
        line.includes("Package Range") ||
        line.includes("Subtotal Per Head") ||
        line.includes("Total Event Cost") ||
        line.includes("Status:")
    );

  const optimizationText = content.includes("Budget Optimization Suggestions:")
    ? content.split("Budget Optimization Suggestions:")[1].split("Pricing Strategy:")[0]
    : "";

  const pricingStrategy = content.includes("Pricing Strategy:")
    ? content.split("Pricing Strategy:")[1]
    : "";

  return (
  <article className="h-[620px] rounded-3xl border border-slate-800 bg-slate-900 shadow-lg overflow-y-auto custom-scrollbar">
    <details open>
      <summary className="sticky top-0 z-20 cursor-pointer border-b border-slate-800 bg-slate-900 p-6 text-xl font-bold text-blue-300">
        Final Quote & Pricing
      </summary>

      <div className="p-6">
        {hasTable && (
          <div className="overflow-auto rounded-xl border border-slate-800">
            <table className="w-full border-collapse text-sm text-slate-300">
              <thead className="sticky top-0 bg-slate-800 text-blue-300">
                <tr>
                  {headers.map((h, i) => (
                    <th
                      key={i}
                      className="border border-slate-700 p-3 text-left uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {bodyRows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-b border-slate-800 hover:bg-slate-800/50"
                  >
                    {row.map((cell, j) => (
                      <td key={j} className="p-3">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {summaryLines.length > 0 && (
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950 p-4 text-sm text-slate-300">
            {summaryLines.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        )}

        <div className="mt-4 border-t border-slate-700 pt-4 text-right text-lg font-bold text-green-400">
          {finalQuote}
        </div>

        {optimizationText && (
          <div className="mt-4 rounded-xl border border-yellow-700 bg-yellow-950/40 p-4">
            <h3 className="mb-2 font-bold text-yellow-300">
              Budget Optimization Suggestions
            </h3>
            <pre className="whitespace-pre-wrap text-sm text-yellow-100 font-sans">
              {optimizationText.trim()}
            </pre>
          </div>
        )}

        {pricingStrategy && (
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950 p-4">
            <h3 className="mb-2 font-bold text-blue-300">
              Pricing Strategy
            </h3>
            <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans">
              {pricingStrategy.trim()}
            </pre>
          </div>
        )}

        {!hasTable && (
          <pre className="whitespace-pre-wrap text-sm text-slate-400 font-mono">
            {content}
          </pre>
        )}
      </div>
    </details>
  </article>
);
}

function Input({
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-blue-500"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
    </label>
  );
}

function getRiskLevel(text: string) {
  const value = text.toLowerCase();

  if (value.includes("risk: high") || value.includes("shortage_detected")) return "HIGH";
  if (value.includes("risk: medium") || value.includes("no_confirmed_shortage")) return "MEDIUM";

  return "LOW";
}

function getInventoryConfidence(text: string) {
  const available = (text.match(/AVAILABLE/g) || []).length;
  const limited = (text.match(/LIMITED/g) || []).length;
  const shortage = (text.match(/CRITICAL SHORTAGE/g) || []).length;
  const unknown = (text.match(/UNKNOWN/g) || []).length;

  const total = available + limited + shortage + unknown;

  if (total === 0) return 70;

  const score =
    ((available * 1.0) +
      (limited * 0.45) +
      (unknown * 0.35) +
      (shortage * 0.0)) /
    total;

  return Math.round(score * 100);
}

function getComplianceConfidence(text: string) {
  const value = text.toLowerCase();

  let score = 100;

  if (value.includes("high risk")) score -= 40;
  if (value.includes("medium risk")) score -= 20;
  if (value.includes("needs verification")) score -= 8;
  if (value.includes("not explicitly addressed")) score -= 5;
  if (value.includes("warning")) score -= 10;

  return Math.max(60, score);
}

function MetricCard({ title, value, type = "default" }: { title: string; value: string; type?: "default" | "success" | "warning" | "danger" }) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
      <p className="text-xs uppercase tracking-widest text-slate-400">{title}</p>
      <p className={`mt-2 text-2xl font-bold ${colorMap[type]}`}>{value}</p>
    </article>
  );
}

function ProcurementSummary({ content }: { content: string }) {
  const available = (content.match(/AVAILABLE/g) || []).length;
  const limited = (content.match(/LIMITED/g) || []).length;
  const shortage = (content.match(/CRITICAL SHORTAGE/g) || []).length;
  const unknown = (content.match(/UNKNOWN/g) || []).length;

  return (
    <section className="grid gap-4 md:grid-cols-4">
      <MetricCard title="Available Items" value={`${available}`} />
      <MetricCard title="Limited Items" value={`${limited}`} />
      <MetricCard title="Shortages" value={`${shortage}`} />
      <MetricCard title="Unknown Items" value={`${unknown}`} />
    </section>
  );
}