"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Complaint = {
  id: string;
  title: string;
  description: string;
  category: string;
  category_confidence: number | null;
  classification_source: string | null;
  severity: string;
  priority_score: number | null;
  status: string;
  sla_deadline?: string | null;
  escalated_at?: string | null;
  // Phase 3
  breach_probability?: number | null;
  escalation_level?: string | null;
  sla_predicted_at?: string | null;
  // Phase 6
  verification_status?: string | null;
  verification_score?: number | null;
  verified_at?: string | null;
  citizen_rating?: number | null;
  citizen_feedback?: string | null;
  created_at: string;
  images?: Array<{ url: string; image_type: string }>;
  assigned_to_name?: string | null;
  timeline?: Array<{ action: string; old_status?: string; new_status?: string; timestamp: string }>;
};
type Worker = { id: string; name: string };
type Analytics = {
  total_complaints: number;
  open_complaints: number;
  critical_complaints: number;
  overdue_complaints: number;
  unassigned_complaints: number;
  resolution_rate: number;
  average_resolution_hours: number | null;
  status_breakdown: Record<string, number>;
  department_workload: Array<{ department_id: number | null; department_name: string; total: number; open: number; overdue: number }>;
  ward_distribution: Array<{ ward_id: number | null; ward_name: string; zone_id: number | null; total: number }>;
  emerging_issues: Array<{ category: string; count: number; open_count: number }>;
};
type AssistantAnswer = {
  question: string;
  intent: string;
  answer: string;
  data: Record<string, unknown>;
  supported_questions: string[];
};
type ClassifyOut = {
  category: string;
  confidence: number;
  source: string;
  severity: string;
  severity_reason: string[];
  suggested_department_id: number;
};
type VerificationReport = {
  complaint_id: string;
  verified: boolean;
  status: string;
  composite_score: number;
  signals: Record<string, unknown>;
  recommendation: string;
  flags: string[];
  evaluated_at: string;
  source: string;
};

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init?.headers },
  });
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as T;
}

function classificationLabel(source: string | null | undefined): string {
  if (!source) return "Unknown";
  if (source === "vision_mobilenet_v3") return "MobileNetV3 Vision AI";
  if (source === "sklearn_text_classifier") return "Text ML";
  if (source === "demo_classifier") return "Keyword Rules";
  return source;
}
function severityColour(s: string): string {
  const map: Record<string, string> = { CRITICAL: "#b91c1c", HIGH: "#c2410c", MEDIUM: "#b45309", LOW: "#15803d" };
  return map[s?.toUpperCase()] ?? "#4b5563";
}
function verificationColour(status: string | null | undefined): string {
  if (!status) return "#6b7280";
  const map: Record<string, string> = {
    verified: "#15803d", provisionally_verified: "#ca8a04",
    needs_review: "#b45309", unverified: "#b91c1c",
    pending: "#6b7280", citizen_rejected: "#b91c1c",
  };
  return map[status] ?? "#6b7280";
}
function escalationColour(level: string | null | undefined): string {
  if (!level) return "#6b7280";
  const map: Record<string, string> = { none: "#15803d", watch: "#ca8a04", escalate: "#c2410c", critical: "#b91c1c" };
  return map[level] ?? "#6b7280";
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div style={S.kpi}>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function ConfidenceMeter({ value, label, dangerAbove }: { value: number | null; label: string; dangerAbove?: number }) {
  if (value === null || value === undefined) return null;
  const pct = Math.round(value * 100);
  const isDanger = dangerAbove !== undefined && value >= dangerAbove;
  const fill = isDanger ? "#b91c1c" : value >= 0.7 ? "#15803d" : value >= 0.4 ? "#ca8a04" : "#6b7280";
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#6b7280", marginBottom: 3 }}>
        <span>{label}</span><span>{pct}%</span>
      </div>
      <div style={{ height: 6, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: fill, borderRadius: 4, transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}

export default function HomePage() {
  const [email, setEmail] = useState("officer.swm@demo.solapur");
  const [password, setPassword] = useState("Demo@1234");
  const [token, setToken] = useState("");
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [workerId, setWorkerId] = useState("");
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantAnswer | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [error, setError] = useState("");
  const [reclassifyResult, setReclassifyResult] = useState<ClassifyOut | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [verificationReport, setVerificationReport] = useState<VerificationReport | null>(null);
  const [verifying, setVerifying] = useState(false);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const login = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!login.ok) throw new Error(await login.text());
      const body = await login.json();
      setToken(body.access_token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed");
    }
  }

  async function loadQueue(authToken = token) {
    try {
      const result = await request<{ data: Complaint[] }>("/api/v1/operations/complaints", authToken);
      setComplaints(result.data);
      const workerResult = await request<Worker[]>("/api/v1/operations/workers", authToken);
      setWorkers(workerResult);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load queue");
    }
  }

  async function loadAnalytics(authToken = token) {
    setAnalyticsLoading(true);
    try {
      const result = await request<Analytics>("/api/v1/analytics/summary", authToken);
      setAnalytics(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load analytics");
    } finally {
      setAnalyticsLoading(false);
    }
  }

  useEffect(() => {
    if (token) { void loadQueue(token); void loadAnalytics(token); }
  }, [token]);

  async function selectComplaint(id: string) {
    setReclassifyResult(null);
    setVerificationReport(null);
    const result = await request<Complaint>(`/api/v1/operations/complaints/${id}`, token);
    setSelected(result);
  }

  async function updateStatus(status: string) {
    if (!selected) return;
    const result = await request<Complaint>(`/api/v1/operations/complaints/${selected.id}/status`, token, {
      method: "PATCH", body: JSON.stringify({ status }),
    });
    setSelected(result);
    await loadQueue();
  }

  async function assignWorker() {
    if (!selected || !workerId.trim()) return;
    const result = await request<Complaint>(`/api/v1/operations/complaints/${selected.id}/assign`, token, {
      method: "POST", body: JSON.stringify({ field_worker_id: workerId.trim() }),
    });
    setSelected(result); setWorkerId(""); await loadQueue();
  }

  async function runSla() {
    try {
      const result = await request<{ reminders_created: number; escalations_created: number }>(
        "/api/v1/operations/sla/run", token, { method: "POST" },
      );
      setError(`SLA checked: ${result.reminders_created} reminder(s), ${result.escalations_created} escalation(s).`);
      await loadQueue();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to run SLA evaluation");
    }
  }

  async function runReclassify() {
    if (!selected) return;
    setReclassifying(true); setReclassifyResult(null);
    try {
      const result = await request<ClassifyOut>(
        `/api/v1/operations/complaints/${selected.id}/reclassify?apply_updates=true`,
        token, { method: "POST" },
      );
      setReclassifyResult(result);
      const refreshed = await request<Complaint>(`/api/v1/operations/complaints/${selected.id}`, token);
      setSelected(refreshed);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Reclassification failed");
    } finally { setReclassifying(false); }
  }

  async function runVerification() {
    if (!selected) return;
    setVerifying(true); setVerificationReport(null);
    try {
      const result = await request<VerificationReport>(
        `/api/v1/operations/complaints/${selected.id}/verify`,
        token, { method: "POST" },
      );
      setVerificationReport(result);
      const refreshed = await request<Complaint>(`/api/v1/operations/complaints/${selected.id}`, token);
      setSelected(refreshed);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Verification failed");
    } finally { setVerifying(false); }
  }

  async function askAssistant(event: FormEvent) {
    event.preventDefault();
    if (!assistantQuestion.trim()) return;
    setAssistantLoading(true); setError("");
    try {
      const result = await request<AssistantAnswer>("/api/v1/assistant/query", token, {
        method: "POST", body: JSON.stringify({ question: assistantQuestion.trim() }),
      });
      setAssistantAnswer(result);
    } catch (reason) {
      setAssistantAnswer(null);
      setError(reason instanceof Error ? reason.message : "Unable to answer question");
    } finally { setAssistantLoading(false); }
  }

  if (!token) {
    return (
      <main style={S.shell}>
        <h1>NagarIQ Operations</h1>
        <p>Officer triage and department assignment</p>
        <form onSubmit={signIn} style={S.form}>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
          <button type="submit">Sign in</button>
        </form>
        {error && <p style={S.error}>{error}</p>}
      </main>
    );
  }

  const activeVerification = verificationReport ?? (
    selected?.verification_status ? {
      complaint_id: selected.id,
      verified: selected.verification_status === "verified",
      status: selected.verification_status,
      composite_score: selected.verification_score ?? 0,
      signals: {}, recommendation: "", flags: [],
      evaluated_at: selected.verified_at ?? "",
      source: "multi_signal_rule_engine",
    } : null
  );

  return (
    <main style={S.shell}>
      <header style={S.header}>
        <div>
          <h1>Officer triage queue</h1>
          <p>Review and assign complaints for your department.</p>
        </div>
        <div style={S.headerActions}>
          <button onClick={() => { void loadQueue(); void loadAnalytics(); }}>Refresh data</button>
          <button onClick={() => void runSla()}>Check SLA</button>
          <button onClick={() => setToken("")}>Sign out</button>
        </div>
      </header>
      {error && <p style={S.error}>{error}</p>}

      {/* Analytics */}
      <section style={S.dashboard} aria-label="Municipal analytics">
        <div style={S.sectionHeader}>
          <div><h2>Municipal intelligence</h2><p>Live workload and accountability signals.</p></div>
          {analyticsLoading && <small>Refreshing...</small>}
        </div>
        {!analytics && analyticsLoading && <p>Loading analytics...</p>}
        {!analytics && !analyticsLoading && <p>No analytics available yet.</p>}
        {analytics && (
          <>
            <div style={S.kpiGrid}>
              <Metric label="Open" value={analytics.open_complaints} />
              <Metric label="Critical" value={analytics.critical_complaints} />
              <Metric label="Overdue" value={analytics.overdue_complaints} />
              <Metric label="Unassigned" value={analytics.unassigned_complaints} />
              <Metric label="Resolution rate" value={`${analytics.resolution_rate}%`} />
              <Metric label="Avg. resolution" value={analytics.average_resolution_hours === null ? "—" : `${analytics.average_resolution_hours}h`} />
            </div>
            <div style={S.analyticsGrid}>
              <div style={S.panel}>
                <h3>Emerging issues</h3>
                {analytics.emerging_issues.length === 0 ? <p>No categories yet.</p> : analytics.emerging_issues.map((issue) => (
                  <div key={issue.category} style={S.metricRow}><span>{issue.category.replaceAll("_", " ")}</span><b>{issue.open_count} open / {issue.count} total</b></div>
                ))}
              </div>
              <div style={S.panel}>
                <h3>Ward distribution</h3>
                {analytics.ward_distribution.length === 0 ? <p>No ward-linked complaints yet.</p> : analytics.ward_distribution.map((w) => (
                  <div key={`${w.ward_id}-${w.zone_id}`} style={S.metricRow}><span>{w.ward_name}</span><b>{w.total}</b></div>
                ))}
              </div>
              <div style={S.panel}>
                <h3>Department workload</h3>
                {analytics.department_workload.length === 0 ? <p>No department workload yet.</p> : analytics.department_workload.map((d) => (
                  <div key={d.department_id ?? "unassigned"} style={S.metricRow}><span>{d.department_name}</span><b>{d.open} open / {d.overdue} overdue</b></div>
                ))}
              </div>
            </div>
          </>
        )}
      </section>

      {/* Assistant */}
      <section style={S.assistant} aria-label="Operations assistant">
        <h2>Operations assistant</h2>
        <p>Ask one of the supported database-backed questions. This assistant does not invent statistics.</p>
        <form onSubmit={askAssistant} style={S.assistantForm}>
          <input value={assistantQuestion} onChange={(e) => setAssistantQuestion(e.target.value)} placeholder="Which department has the highest workload?" aria-label="Operational question" />
          <button type="submit" disabled={assistantLoading}>{assistantLoading ? "Thinking..." : "Ask"}</button>
        </form>
        {assistantAnswer && (
          <div style={S.answer}>
            <strong>{assistantAnswer.answer}</strong>
            <small>Source: SQL rules · {assistantAnswer.intent}</small>
            <details><summary>Supported questions</summary><ul>{assistantAnswer.supported_questions.map((q) => <li key={q}>{q}</li>)}</ul></details>
          </div>
        )}
      </section>

      {/* Main triage layout */}
      <section style={S.layout}>
        {/* Left: complaint list */}
        <div>
          {complaints.length === 0 ? <p>No complaints in this department.</p> : complaints.map((c) => (
            <button key={c.id} onClick={() => void selectComplaint(c.id)}
              style={{ ...S.card, borderLeft: `4px solid ${severityColour(c.severity)}`, background: selected?.id === c.id ? "#f0f7f4" : "white" }}>
              <strong>{c.title}</strong>
              <span style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                <span>{c.category.replaceAll("_", " ")}</span>
                <span style={{ ...S.badge, background: severityColour(c.severity), color: "#fff" }}>{c.severity}</span>
                <span style={S.statusPill}>{c.status.replaceAll("_", " ")}</span>
              </span>
              {c.classification_source && (
                <span style={S.aiChip}>
                  {"\u{1F916}"} {classificationLabel(c.classification_source)}
                  {c.category_confidence != null ? ` \u00B7 ${Math.round(c.category_confidence * 100)}%` : ""}
                </span>
              )}
              {c.breach_probability != null && (
                <span style={{ ...S.aiChip, background: c.breach_probability >= 0.6 ? "#fef2f2" : "#f0fdf4", color: c.breach_probability >= 0.6 ? "#b91c1c" : "#15803d" }}>
                  {"\u26A0"} SLA risk {Math.round(c.breach_probability * 100)}%
                  {c.escalation_level && c.escalation_level !== "none" ? ` \u00B7 ${c.escalation_level}` : ""}
                </span>
              )}
              <small>{new Date(c.created_at).toLocaleString()}</small>
            </button>
          ))}
        </div>

        {/* Right: complaint detail */}
        {selected && (
          <article style={S.detail}>
            <h2>{selected.title}</h2>
            <p>{selected.description}</p>
            <div style={S.metaGrid}>
              <div><b>Status</b><span style={S.statusPill}>{selected.status.replaceAll("_", " ")}</span></div>
              <div><b>Severity</b><span style={{ ...S.badge, background: severityColour(selected.severity), color: "#fff" }}>{selected.severity}</span></div>
              <div><b>SLA deadline</b><span>{selected.sla_deadline ? new Date(selected.sla_deadline).toLocaleString() : "Not configured"}</span></div>
              <div><b>Assigned to</b><span>{selected.assigned_to_name ?? "Unassigned"}</span></div>
            </div>
            {selected.escalated_at && <p style={S.warning}>{"\u26A1"} Escalated {new Date(selected.escalated_at).toLocaleString()}</p>}

            {/* Photos */}
            {(() => {
              const before = selected.images?.find((i) => i.image_type === "before");
              const after = selected.images?.find((i) => i.image_type === "after");
              const fallback = !before ? selected.images?.[0] : undefined;
              return (
                <>
                  {(before ?? fallback) && (
                    <div style={S.photoWrap}>
                      <p style={S.photoLabel}>{"\uD83D\uDCF7"} {before ? "Complaint evidence (before)" : "Complaint photo"}</p>
                      <img src={`${API}${(before ?? fallback)!.url}`} alt="Complaint evidence" style={S.photo} />
                    </div>
                  )}
                  {after && (
                    <div style={S.photoWrap}>
                      <p style={S.photoLabel}>{"\u2705"} Resolution evidence (after)</p>
                      <img src={`${API}${after.url}`} alt="Resolution evidence" style={S.photo} />
                    </div>
                  )}
                </>
              );
            })()}

            {/* AI Intelligence Card */}
            <div style={S.aiCard}>
              <h3 style={S.aiCardTitle}>{"\u{1F916}"} AI Intelligence</h3>

              {/* Classification */}
              <div style={S.aiSection}>
                <div style={S.aiSectionHeader}>
                  <span style={S.aiSectionLabel}>Vision / ML Classification</span>
                  <button onClick={() => void runReclassify()} disabled={reclassifying} style={S.aiButton}>
                    {reclassifying ? "Analysing\u2026" : "\u25B6 Run Vision AI Triage"}
                  </button>
                </div>
                <div style={S.aiResultBox}>
                  <div style={S.aiResultRow}>
                    <span style={S.aiCategoryLabel}>
                      {(reclassifyResult?.category ?? selected.category).replaceAll("_", " ").toUpperCase()}
                    </span>
                    {(reclassifyResult?.confidence ?? selected.category_confidence) != null && (
                      <span style={{ ...S.badge, background: "#1d4ed8", color: "#fff" }}>
                        {Math.round(((reclassifyResult?.confidence ?? selected.category_confidence)!) * 100)}% confidence
                      </span>
                    )}
                    <span style={S.sourceTag}>{classificationLabel(reclassifyResult?.source ?? selected.classification_source)}</span>
                  </div>
                  {reclassifyResult && (
                    <>
                      <span style={{ ...S.badge, background: severityColour(reclassifyResult.severity), color: "#fff" }}>{reclassifyResult.severity}</span>
                      {reclassifyResult.severity_reason.length > 0 && (
                        <p style={S.aiNote}>Reason: {reclassifyResult.severity_reason.join(", ")}</p>
                      )}
                    </>
                  )}
                </div>
                <ConfidenceMeter value={reclassifyResult?.confidence ?? selected.category_confidence ?? null} label="Classification confidence" />
              </div>

              {/* SLA Risk */}
              {selected.breach_probability != null && (
                <div style={S.aiSection}>
                  <span style={S.aiSectionLabel}>SLA Breach Risk (Phase 3)</span>
                  <div style={S.aiResultBox}>
                    <div style={S.aiResultRow}>
                      <span style={S.aiCategoryLabel}>{Math.round(selected.breach_probability * 100)}% breach probability</span>
                      <span style={{ ...S.badge, background: escalationColour(selected.escalation_level), color: "#fff" }}>{selected.escalation_level ?? "none"}</span>
                    </div>
                    <ConfidenceMeter value={selected.breach_probability} label="Risk level" dangerAbove={0.6} />
                    {selected.sla_predicted_at && <p style={S.aiNote}>Predicted at {new Date(selected.sla_predicted_at).toLocaleString()}</p>}
                  </div>
                </div>
              )}

              {/* Verification */}
              <div style={S.aiSection}>
                <div style={S.aiSectionHeader}>
                  <span style={S.aiSectionLabel}>Resolution Verification (Phase 6)</span>
                  <button onClick={() => void runVerification()} disabled={verifying} style={S.aiButton}>
                    {verifying ? "Verifying\u2026" : "\u25B6 Run Multi-Signal Check"}
                  </button>
                </div>
                {activeVerification ? (
                  <div style={S.aiResultBox}>
                    <div style={S.aiResultRow}>
                      <span style={{ ...S.badge, background: verificationColour(activeVerification.status), color: "#fff" }}>
                        {activeVerification.status.replaceAll("_", " ")}
                      </span>
                      <span style={S.aiCategoryLabel}>Score: {Math.round(activeVerification.composite_score * 100)}%</span>
                    </div>
                    <ConfidenceMeter value={activeVerification.composite_score} label="Verification confidence" />
                    {activeVerification.recommendation && <p style={S.aiNote}>{"\uD83D\uDCAC"} {activeVerification.recommendation}</p>}
                    {activeVerification.flags.length > 0 && (
                      <p style={{ ...S.aiNote, color: "#b91c1c" }}>{"\uD83D\uDEA9"} {activeVerification.flags.join(" \u00B7 ")}</p>
                    )}
                    {Object.keys(activeVerification.signals).length > 0 && (
                      <details style={{ marginTop: 8 }}>
                        <summary style={{ cursor: "pointer", fontSize: 12, color: "#4b5563" }}>Signal breakdown</summary>
                        <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                          {Object.entries(activeVerification.signals).map(([key, sig]) => {
                            const sv = sig as { passed?: boolean; score?: number; status?: string; details?: string };
                            return (
                              <div key={key} style={{ ...S.signalRow, borderLeft: `3px solid ${sv.passed ? "#15803d" : "#b91c1c"}` }}>
                                <span style={{ fontWeight: 600, fontSize: 12 }}>{key.replaceAll("_", " ")}</span>
                                <span style={{ fontSize: 12, color: "#4b5563" }}>
                                  {sv.passed ? "\u2713" : "\u2717"} {sv.status?.replaceAll("_", " ")} \u00B7 {Math.round((sv.score ?? 0) * 100)}%
                                </span>
                                {sv.details && <span style={{ fontSize: 11, color: "#6b7280" }}>{sv.details}</span>}
                              </div>
                            );
                          })}
                        </div>
                      </details>
                    )}
                    {selected.citizen_rating != null && (
                      <p style={S.aiNote}>
                        {"\u2B50"} Citizen rated {selected.citizen_rating}/5
                        {selected.citizen_feedback ? ` \u2014 "${selected.citizen_feedback}"` : ""}
                      </p>
                    )}
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: "#6b7280", marginTop: 6 }}>
                    No verification run yet. Click &quot;Run Multi-Signal Check&quot; after a resolution photo is uploaded.
                  </p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div style={S.actions}>
              {(selected.status === "submitted" || selected.status === "reopened") && (
                <button onClick={() => void updateStatus("under_review")} style={S.actionBtn}>Start review</button>
              )}
              {selected.status === "under_review" && (
                <>
                  <button onClick={() => void updateStatus("rejected")} style={{ ...S.actionBtn, background: "#fef2f2", color: "#b91c1c" }}>Reject</button>
                  <select value={workerId} onChange={(e) => setWorkerId(e.target.value)} style={S.select}>
                    <option value="">Select field worker</option>
                    {workers.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                  </select>
                  <button onClick={() => void assignWorker()} style={S.actionBtn}>Assign worker</button>
                </>
              )}
              {selected.status === "resolution_submitted" && (
                <button onClick={() => void updateStatus("verified")} style={{ ...S.actionBtn, background: "#f0fdf4", color: "#15803d" }}>
                  {"\u2713"} Verify resolution evidence
                </button>
              )}
            </div>

            {/* Timeline */}
            <h3>Timeline</h3>
            {selected.timeline && selected.timeline.length > 0 ? (
              <div style={S.timeline}>
                {selected.timeline.map((ev, idx) => (
                  <div key={`${ev.timestamp}-${idx}`} style={S.timelineItem}>
                    <span style={S.timelineDot} />
                    <div>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{ev.action.replaceAll("_", " ")}</span>
                      {ev.new_status && <span style={{ fontSize: 12, color: "#6b7280" }}> {"\u2192"} {ev.new_status.replaceAll("_", " ")}</span>}
                      <div style={{ fontSize: 11, color: "#9ca3af" }}>{new Date(ev.timestamp).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p style={{ color: "#9ca3af", fontSize: 13 }}>No timeline events yet.</p>}
          </article>
        )}
      </section>
    </main>
  );
}

const S = {
  shell: { maxWidth: 1200, margin: "40px auto", padding: 24, fontFamily: "'Inter','Segoe UI',Arial,sans-serif", color: "#111827" },
  form: { display: "grid", gap: 12, maxWidth: 420 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  headerActions: { display: "flex", gap: 8 },
  layout: { display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(360px,1.2fr)", gap: 24 },
  dashboard: { margin: "24px 0", padding: 20, background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10 },
  sectionHeader: { display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 10, margin: "16px 0" },
  kpi: { display: "grid", gap: 6, padding: 14, background: "white", border: "1px solid #d1fae5", borderRadius: 8 },
  analyticsGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 },
  panel: { padding: 16, background: "white", border: "1px solid #d1fae5", borderRadius: 8 },
  metricRow: { display: "flex", justifyContent: "space-between", gap: 12, padding: "8px 0", borderBottom: "1px solid #f0fdf4" },
  assistant: { margin: "24px 0", padding: 20, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10 },
  assistantForm: { display: "flex", gap: 8, maxWidth: 760 },
  answer: { display: "grid", gap: 8, marginTop: 16, padding: 14, background: "#fff", border: "1px solid #fde68a", borderRadius: 8 },
  card: { display: "grid", gap: 6, width: "100%", textAlign: "left" as const, padding: 14, marginBottom: 10, background: "white", border: "1px solid #e5e7eb", borderRadius: 10, cursor: "pointer" },
  detail: { padding: 22, background: "#f9fafb", borderRadius: 10, border: "1px solid #e5e7eb" },
  photo: { width: "100%", maxHeight: 220, objectFit: "contain" as const, background: "#fff", borderRadius: 8, border: "1px solid #e5e7eb" },
  photoWrap: { marginBottom: 14 },
  photoLabel: { fontSize: 12, color: "#6b7280", margin: "0 0 4px" },
  error: { color: "#b91c1c" },
  warning: { color: "#c2410c", fontWeight: 600, fontSize: 13 },
  metaGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, margin: "12px 0", fontSize: 13 },
  badge: { display: "inline-block", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 700 },
  statusPill: { display: "inline-block", padding: "2px 8px", borderRadius: 12, fontSize: 11, background: "#e5e7eb", color: "#374151" },
  aiChip: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" },
  aiCard: { margin: "16px 0", padding: 16, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 },
  aiCardTitle: { fontSize: 14, fontWeight: 700, margin: "0 0 12px", color: "#1f2937" },
  aiSection: { marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid #f3f4f6" },
  aiSectionHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  aiSectionLabel: { fontSize: 12, fontWeight: 600, color: "#4b5563", textTransform: "uppercase" as const, letterSpacing: "0.05em" },
  aiButton: { padding: "4px 10px", fontSize: 12, background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
  aiResultBox: { background: "#f9fafb", borderRadius: 8, padding: 10, display: "grid", gap: 6 },
  aiResultRow: { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" as const },
  aiCategoryLabel: { fontSize: 13, fontWeight: 700, color: "#111827" },
  sourceTag: { fontSize: 11, padding: "2px 8px", background: "#dbeafe", color: "#1e40af", borderRadius: 10, fontWeight: 600 },
  aiNote: { fontSize: 12, color: "#6b7280", margin: 0, lineHeight: 1.5 },
  signalRow: { padding: "4px 8px", background: "#f9fafb", borderRadius: 4, display: "grid", gap: 2 },
  actions: { display: "flex", gap: 8, flexWrap: "wrap" as const, margin: "16px 0" },
  actionBtn: { padding: "8px 16px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 13 },
  select: { padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13 },
  timeline: { display: "grid", gap: 8, marginTop: 8 },
  timelineItem: { display: "flex", gap: 10, alignItems: "flex-start" },
  timelineDot: { width: 8, height: 8, borderRadius: "50%", background: "#6b7280", marginTop: 4, flexShrink: 0 },
};
