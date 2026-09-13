"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────
type Complaint = {
  id: string; title: string; description: string;
  category: string; category_confidence: number | null;
  classification_source: string | null; severity: string;
  priority_score: number | null; priority_label: string | null;
  priority_reasons: string[] | null; status: string;
  sla_deadline?: string | null; escalated_at?: string | null;
  breach_probability?: number | null; escalation_level?: string | null;
  sla_predicted_at?: string | null; verification_status?: string | null;
  verification_score?: number | null; verified_at?: string | null;
  citizen_rating?: number | null; citizen_feedback?: string | null;
  created_at: string; location_lat?: number; location_lng?: number;
  ward_name?: string | null; ward_id?: number | null;
  images?: Array<{ url: string; image_type: string }>;
  assigned_to?: string | null; assigned_to_name?: string | null;
  related_count?: number;
  timeline?: Array<{ action: string; old_status?: string; new_status?: string; timestamp: string }>;
};
type Worker = { id: string; name: string };
type Analytics = {
  total_complaints: number; open_complaints: number;
  critical_complaints: number; overdue_complaints: number;
  unassigned_complaints: number; resolution_rate: number;
  average_resolution_hours: number | null;
  status_breakdown: Record<string, number>;
  department_workload: Array<{ department_id: number | null; department_name: string; total: number; open: number; overdue: number }>;
  ward_distribution: Array<{ ward_id: number | null; ward_name: string; zone_id: number | null; total: number }>;
  emerging_issues: Array<{ category: string; count: number; open_count: number }>;
};
type Crisis = {
  category: string; ward_id: number | null; ward_name: string;
  current_count: number; previous_count: number; pct_increase: number;
  open_count: number; recommendation: string; severity: string;
};
type WorkerRec = {
  worker_id: string; worker_name: string; active_tasks: number;
  distance_km: number | null; department_match: boolean; score: number; reason: string;
};
type AssistantAnswer = {
  question: string; intent: string; answer: string;
  data: Record<string, unknown>; supported_questions: string[];
};
type ClassifyOut = {
  category: string; confidence: number; source: string;
  severity: string; severity_reason: string[]; suggested_department_id: number;
};
type VerificationReport = {
  complaint_id: string; verified: boolean; status: string;
  composite_score: number; signals: Record<string, unknown>;
  recommendation: string; flags: string[]; evaluated_at: string; source: string;
};

// ── Helpers ────────────────────────────────────────────────────────────────
async function req<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const headers: Record<string, string> = isForm
    ? { Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

function sevColor(s: string) {
  return ({ CRITICAL: "#b91c1c", HIGH: "#c2410c", MEDIUM: "#b45309", LOW: "#15803d" } as Record<string, string>)[s?.toUpperCase()] ?? "#6b7280";
}
function statusColor(s: string) {
  return ({
    submitted: "#1d4ed8", under_review: "#7c3aed", assigned: "#0891b2",
    in_progress: "#d97706", resolution_submitted: "#059669",
    verified: "#15803d", closed: "#374151", rejected: "#b91c1c", reopened: "#c2410c",
  } as Record<string, string>)[s] ?? "#6b7280";
}
function verColor(s: string | null | undefined) {
  return ({
    verified: "#15803d", provisionally_verified: "#ca8a04",
    needs_review: "#b45309", unverified: "#b91c1c", pending: "#6b7280", citizen_rejected: "#b91c1c",
  } as Record<string, string>)[s ?? ""] ?? "#6b7280";
}
function escColor(l: string | null | undefined) {
  return ({ none: "#15803d", watch: "#ca8a04", escalate: "#c2410c", critical: "#b91c1c" } as Record<string, string>)[l ?? ""] ?? "#6b7280";
}
function classLabel(src: string | null | undefined) {
  if (!src) return "Unknown";
  if (src === "vision_mobilenet_v3") return "Vision AI";
  if (src.startsWith("sklearn_text")) return "Text ML";
  if (src === "demo_classifier") return "Keyword";
  return src;
}
function catEmoji(c: string) {
  return ({ garbage: "🗑️", pothole: "🕳️", drainage: "🌊", streetlight: "💡", water_leakage: "💧", other: "📋" } as Record<string, string>)[c] ?? "📋";
}
function fmtTime(iso: string) { return new Date(iso).toLocaleString(); }
function fmtDate(iso: string) { return new Date(iso).toLocaleDateString(); }
function elapsed(iso: string) {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3600000);
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`;
}
function slaStatus(deadline: string | null | undefined, breach: number | null | undefined): { label: string; color: string; icon: string } {
  if (!deadline) return { label: "No SLA", color: "#6b7280", icon: "⚪" };
  const rem = new Date(deadline).getTime() - Date.now();
  if (rem < 0) return { label: "Breached", color: "#b91c1c", icon: "🔴" };
  if (breach != null && breach >= 0.7) return { label: "High risk", color: "#c2410c", icon: "🟠" };
  if (rem < 2 * 3600000) return { label: "At risk", color: "#b45309", icon: "🟡" };
  return { label: "On track", color: "#15803d", icon: "🟢" };
}

// ── Small UI components ────────────────────────────────────────────────────
function Badge({ label, color, bg }: { label: string; color: string; bg: string }) {
  return <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 700, color, background: bg }}>{label}</span>;
}
function Pill({ label }: { label: string }) {
  return <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, background: "#f3f4f6", color: "#374151" }}>{label.replaceAll("_", " ")}</span>;
}
function KPI({ label, value, sub, warn }: { label: string; value: string | number; sub?: string; warn?: boolean }) {
  return (
    <div style={{ padding: "16px 18px", background: "#fff", border: `1px solid ${warn ? "#fecaca" : "#e5e7eb"}`, borderRadius: 10, display: "grid", gap: 3 }}>
      <div style={{ fontSize: 11, color: "#6b7280", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: warn ? "#b91c1c" : "#111827" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#9ca3af" }}>{sub}</div>}
    </div>
  );
}
function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: 6, background: "#e5e7eb", borderRadius: 4, overflow: "hidden", marginTop: 4 }}>
      <div style={{ width: `${Math.min(100, pct)}%`, height: "100%", background: color, borderRadius: 4 }} />
    </div>
  );
}
function ConfBar({ value, label, dangerAbove }: { value: number | null; label: string; dangerAbove?: number }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  const isDanger = dangerAbove != null && value >= dangerAbove;
  const fill = isDanger ? "#b91c1c" : value >= 0.7 ? "#15803d" : value >= 0.4 ? "#ca8a04" : "#6b7280";
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#6b7280", marginBottom: 2 }}>
        <span>{label}</span><span>{pct}%</span>
      </div>
      <Bar pct={pct} color={fill} />
    </div>
  );
}
function Section({ title, children, accent }: { title: string; children: React.ReactNode; accent?: string }) {
  return (
    <div style={{ background: "#fff", border: `1px solid ${accent ?? "#e5e7eb"}`, borderRadius: 12, padding: 18, marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#111827", marginBottom: 12, borderBottom: "1px solid #f3f4f6", paddingBottom: 8 }}>{title}</div>
      {children}
    </div>
  );
}
function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #f9fafb", fontSize: 13 }}>
      <span style={{ color: "#6b7280", fontWeight: 500 }}>{label}</span>
      <span style={{ color: "#111827", fontWeight: 600 }}>{value}</span>
    </div>
  );
}
function Btn({ label, onClick, disabled, variant }: { label: string; onClick: () => void; disabled?: boolean; variant?: "primary" | "danger" | "success" | "ghost" }) {
  const styles: Record<string, React.CSSProperties> = {
    primary: { background: "#1d4ed8", color: "#fff", border: "none" },
    danger: { background: "#fef2f2", color: "#b91c1c", border: "1px solid #fecaca" },
    success: { background: "#f0fdf4", color: "#15803d", border: "1px solid #bbf7d0" },
    ghost: { background: "#f9fafb", color: "#374151", border: "1px solid #e5e7eb" },
  };
  return (
    <button onClick={onClick} disabled={disabled}
      style={{ padding: "7px 14px", borderRadius: 8, cursor: disabled ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600, opacity: disabled ? 0.5 : 1, ...(styles[variant ?? "ghost"]) }}>
      {label}
    </button>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function HomePage() {
  const [email, setEmail] = useState("officer.swm@demo.solapur");
  const [password, setPassword] = useState("Demo@1234");
  const [token, setToken] = useState("");
  const [tab, setTab] = useState<"command" | "queue" | "assistant">("command");
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [workerRecs, setWorkerRecs] = useState<WorkerRec[]>([]);
  const [workerId, setWorkerId] = useState("");
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [crises, setCrises] = useState<Crisis[]>([]);
  const [assistantQ, setAssistantQ] = useState("");
  const [assistantA, setAssistantA] = useState<AssistantAnswer | null>(null);
  const [reclassify, setReclassify] = useState<ClassifyOut | null>(null);
  const [verification, setVerification] = useState<VerificationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [filterSev, setFilterSev] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const loadAll = useCallback(async (t: string) => {
    try {
      const [q, w, a] = await Promise.all([
        req<{ data: Complaint[] }>("/api/v1/operations/complaints", t),
        req<Worker[]>("/api/v1/operations/workers", t),
        req<Analytics>("/api/v1/analytics/summary", t),
      ]);
      setComplaints(q.data);
      setWorkers(w);
      setAnalytics(a);
      try {
        const c = await req<Crisis[]>("/api/v1/analytics/emerging-crises", t);
        setCrises(c);
      } catch { setCrises([]); }
    } catch (e) { setError(e instanceof Error ? e.message : "Load failed"); }
  }, []);

  useEffect(() => { if (token) void loadAll(token); }, [token, loadAll]);

  async function signIn(e: FormEvent) {
    e.preventDefault(); setError("");
    try {
      const r = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) throw new Error(await r.text());
      const b = await r.json();
      setToken(b.access_token);
    } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); }
  }

  async function selectComplaint(id: string) {
    setReclassify(null); setVerification(null); setWorkerRecs([]);
    try {
      const c = await req<Complaint>(`/api/v1/operations/complaints/${id}`, token);
      setSelected(c);
      try {
        const recs = await req<WorkerRec[]>(`/api/v1/operations/complaints/${id}/worker-recommendations`, token);
        setWorkerRecs(recs);
      } catch { setWorkerRecs([]); }
    } catch (e) { setError(e instanceof Error ? e.message : "Load failed"); }
  }

  async function updateStatus(status: string) {
    if (!selected) return;
    try {
      const r = await req<Complaint>(`/api/v1/operations/complaints/${selected.id}/status`, token, { method: "PATCH", body: JSON.stringify({ status }) });
      setSelected(r); await loadAll(token);
    } catch (e) { setError(e instanceof Error ? e.message : "Update failed"); }
  }

  async function assignWorker(wid: string) {
    if (!selected) return;
    try {
      const r = await req<Complaint>(`/api/v1/operations/complaints/${selected.id}/assign`, token, { method: "POST", body: JSON.stringify({ field_worker_id: wid }) });
      setSelected(r); setWorkerId(""); await loadAll(token);
    } catch (e) { setError(e instanceof Error ? e.message : "Assign failed"); }
  }

  async function runReclassify() {
    if (!selected) return; setLoading(true);
    try {
      const r = await req<ClassifyOut>(`/api/v1/operations/complaints/${selected.id}/reclassify?apply_updates=true`, token, { method: "POST" });
      setReclassify(r);
      const refreshed = await req<Complaint>(`/api/v1/operations/complaints/${selected.id}`, token);
      setSelected(refreshed);
    } catch (e) { setError(e instanceof Error ? e.message : "Reclassify failed"); }
    finally { setLoading(false); }
  }

  async function runVerify() {
    if (!selected) return; setLoading(true);
    try {
      const r = await req<VerificationReport>(`/api/v1/operations/complaints/${selected.id}/verify`, token, { method: "POST" });
      setVerification(r);
      const refreshed = await req<Complaint>(`/api/v1/operations/complaints/${selected.id}`, token);
      setSelected(refreshed);
    } catch (e) { setError(e instanceof Error ? e.message : "Verify failed"); }
    finally { setLoading(false); }
  }

  async function runSla() {
    try {
      const r = await req<{ reminders_created: number; escalations_created: number }>("/api/v1/operations/sla/run", token, { method: "POST" });
      setError(`SLA: ${r.reminders_created} reminder(s), ${r.escalations_created} escalation(s)`);
      await loadAll(token);
    } catch (e) { setError(e instanceof Error ? e.message : "SLA failed"); }
  }

  async function askAssistant(e: FormEvent) {
    e.preventDefault(); if (!assistantQ.trim()) return; setLoading(true);
    try {
      const r = await req<AssistantAnswer>("/api/v1/assistant/query", token, { method: "POST", body: JSON.stringify({ question: assistantQ }) });
      setAssistantA(r);
    } catch (e) { setError(e instanceof Error ? e.message : "Assistant failed"); }
    finally { setLoading(false); }
  }

  const filtered = complaints.filter(c =>
    (!filterCat || c.category === filterCat) &&
    (!filterSev || c.severity === filterSev) &&
    (!filterStatus || c.status === filterStatus)
  );

  // ── Login ──────────────────────────────────────────────────────────────
  if (!token) return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f8fafc", fontFamily: "'Inter','Segoe UI',Arial,sans-serif" }}>
      <div style={{ width: 380, padding: 32, background: "#fff", borderRadius: 16, border: "1px solid #e5e7eb", boxShadow: "0 4px 24px rgba(0,0,0,0.08)" }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#111827" }}>NagarSetu</div>
          <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>Municipal Operations Console · Solapur</div>
        </div>
        <form onSubmit={signIn} style={{ display: "grid", gap: 12 }}>
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email"
            style={{ padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14 }} />
          <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Password"
            style={{ padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14 }} />
          <button type="submit" style={{ padding: "10px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: "pointer" }}>Sign in</button>
        </form>
        {error && <div style={{ marginTop: 12, color: "#b91c1c", fontSize: 13 }}>{error}</div>}
        <div style={{ marginTop: 16, fontSize: 11, color: "#9ca3af" }}>
          Demo: officer.swm@demo.solapur / admin@demo.solapur · Password: Demo@1234
        </div>
      </div>
    </main>
  );

  // ── Shell ──────────────────────────────────────────────────────────────
  return (
    <main style={{ fontFamily: "'Inter','Segoe UI',Arial,sans-serif", background: "#f8fafc", minHeight: "100vh", color: "#111827" }}>
      {/* Top bar */}
      <div style={{ background: "#fff", borderBottom: "1px solid #e5e7eb", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 52 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: "#111827" }}>NagarSetu</span>
          <span style={{ fontSize: 11, color: "#9ca3af" }}>Solapur Municipal Intelligence</span>
          {(["command", "queue", "assistant"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              style={{ padding: "4px 12px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, background: tab === t ? "#eff6ff" : "transparent", color: tab === t ? "#1d4ed8" : "#6b7280" }}>
              {t === "command" ? "Command Center" : t === "queue" ? "Complaint Queue" : "Assistant"}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Btn label="Refresh" onClick={() => void loadAll(token)} variant="ghost" />
          <Btn label="Run SLA" onClick={() => void runSla()} variant="ghost" />
          <Btn label="Sign out" onClick={() => setToken("")} variant="ghost" />
        </div>
      </div>

      {error && <div style={{ margin: "12px 24px 0", padding: "8px 14px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, fontSize: 13, color: "#b91c1c" }}>{error}</div>}

      <div style={{ padding: "20px 24px" }}>
        {tab === "command" && <CommandCenter analytics={analytics} crises={crises} />}
        {tab === "queue" && (
          <QueueTab
            complaints={filtered} selected={selected} workers={workers} workerRecs={workerRecs}
            workerId={workerId} setWorkerId={setWorkerId} loading={loading}
            filterCat={filterCat} setFilterCat={setFilterCat}
            filterSev={filterSev} setFilterSev={setFilterSev}
            filterStatus={filterStatus} setFilterStatus={setFilterStatus}
            reclassify={reclassify} verification={verification}
            onSelect={id => void selectComplaint(id)}
            onStatus={s => void updateStatus(s)}
            onAssign={id => void assignWorker(id)}
            onReclassify={() => void runReclassify()}
            onVerify={() => void runVerify()}
          />
        )}
        {tab === "assistant" && (
          <AssistantTab question={assistantQ} setQuestion={setAssistantQ} answer={assistantA} loading={loading} onAsk={e => void askAssistant(e)} />
        )}
      </div>
    </main>
  );
}

// ── Command Center Tab ─────────────────────────────────────────────────────
function CommandCenter({ analytics, crises }: { analytics: Analytics | null; crises: Crisis[] }) {
  if (!analytics) return <div style={{ color: "#6b7280", padding: 40, textAlign: "center" }}>Loading command center data...</div>;
  const a = analytics;
  const maxDept = Math.max(...a.department_workload.map(d => d.total), 1);
  const maxWard = Math.max(...a.ward_distribution.map(w => w.total), 1);

  return (
    <div>
      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginBottom: 20 }}>
        <KPI label="Total" value={a.total_complaints} />
        <KPI label="Open" value={a.open_complaints} sub={`${a.resolution_rate}% resolved`} />
        <KPI label="Critical" value={a.critical_complaints} warn={a.critical_complaints > 0} />
        <KPI label="Overdue" value={a.overdue_complaints} warn={a.overdue_complaints > 0} />
        <KPI label="Unassigned" value={a.unassigned_complaints} warn={a.unassigned_complaints > 0} />
        <KPI label="Avg Resolution" value={a.average_resolution_hours != null ? `${a.average_resolution_hours}h` : "—"} />
      </div>

      {/* Status breakdown */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 16, marginBottom: 16 }}>
        <Section title="📊 Status Breakdown">
          {Object.entries(a.status_breakdown).filter(([, v]) => v > 0).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid #f9fafb", fontSize: 13 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor(k), display: "inline-block" }} />
                {k.replaceAll("_", " ")}
              </span>
              <strong>{v}</strong>
            </div>
          ))}
        </Section>

        {/* Emerging crises */}
        <Section title="🚨 Emerging Crisis Detection" accent={crises.length > 0 ? "#fecaca" : "#e5e7eb"}>
          {crises.length === 0 ? (
            <div style={{ color: "#6b7280", fontSize: 13, padding: "8px 0" }}>
              No emerging crises detected in the current window.<br />
              <span style={{ fontSize: 11, color: "#9ca3af" }}>Requires sufficient historical data to compare windows.</span>
            </div>
          ) : crises.map((c, i) => (
            <div key={i} style={{ background: c.severity === "critical" ? "#fef2f2" : "#fffbeb", border: `1px solid ${c.severity === "critical" ? "#fecaca" : "#fde68a"}`, borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontWeight: 700, fontSize: 13 }}>{catEmoji(c.category)} {c.category.replaceAll("_", " ")} · {c.ward_name}</span>
                <Badge label={c.severity.toUpperCase()} color="#fff" bg={c.severity === "critical" ? "#b91c1c" : "#d97706"} />
              </div>
              <div style={{ fontSize: 12, color: "#374151", marginBottom: 4 }}>
                <strong>+{c.pct_increase}%</strong> vs previous period · {c.current_count} complaints ({c.open_count} open)
              </div>
              <div style={{ fontSize: 11, color: "#6b7280" }}>{c.recommendation}</div>
            </div>
          ))}
        </Section>
      </div>

      {/* Department + Ward */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 16 }}>
        <Section title="🏢 Department Health">
          {a.department_workload.length === 0 ? <div style={{ color: "#9ca3af", fontSize: 13 }}>No data yet.</div> :
            a.department_workload.map(d => (
              <div key={d.department_id ?? "none"} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 2 }}>
                  <span style={{ fontWeight: 600 }}>{d.department_name}</span>
                  <span style={{ color: "#6b7280" }}>{d.open} open · {d.overdue > 0 ? <span style={{ color: "#b91c1c" }}>{d.overdue} overdue</span> : "0 overdue"}</span>
                </div>
                <Bar pct={(d.total / maxDept) * 100} color={d.overdue > 0 ? "#c2410c" : "#1d4ed8"} />
              </div>
            ))}
        </Section>

        <Section title="🗺️ Ward Distribution">
          {a.ward_distribution.length === 0 ? <div style={{ color: "#9ca3af", fontSize: 13 }}>No ward-linked complaints yet.</div> :
            a.ward_distribution.slice(0, 10).map(w => (
              <div key={w.ward_id ?? "none"} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 2 }}>
                  <span style={{ fontWeight: 600 }}>{w.ward_name}</span>
                  <span style={{ color: "#6b7280" }}>{w.total}</span>
                </div>
                <Bar pct={(w.total / maxWard) * 100} color="#7c3aed" />
              </div>
            ))}
        </Section>
      </div>
    </div>
  );
}

// ── Queue Tab ──────────────────────────────────────────────────────────────
const CATS = ["garbage", "pothole", "drainage", "streetlight", "water_leakage", "other"];
const SEVS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const STATUSES = ["submitted", "under_review", "assigned", "in_progress", "resolution_submitted", "verified", "closed", "rejected", "reopened"];

function QueueTab({ complaints, selected, workers, workerRecs, workerId, setWorkerId, loading,
  filterCat, setFilterCat, filterSev, setFilterSev, filterStatus, setFilterStatus,
  reclassify, verification, onSelect, onStatus, onAssign, onReclassify, onVerify }: {
  complaints: Complaint[]; selected: Complaint | null; workers: Worker[]; workerRecs: WorkerRec[];
  workerId: string; setWorkerId: (v: string) => void; loading: boolean;
  filterCat: string; setFilterCat: (v: string) => void;
  filterSev: string; setFilterSev: (v: string) => void;
  filterStatus: string; setFilterStatus: (v: string) => void;
  reclassify: ClassifyOut | null; verification: VerificationReport | null;
  onSelect: (id: string) => void; onStatus: (s: string) => void;
  onAssign: (id: string) => void; onReclassify: () => void; onVerify: () => void;
}) {
  return (
    <div>
      {/* Filters */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13 }}>
          <option value="">All categories</option>
          {CATS.map(c => <option key={c} value={c}>{c.replaceAll("_", " ")}</option>)}
        </select>
        <select value={filterSev} onChange={e => setFilterSev(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13 }}>
          <option value="">All severities</option>
          {SEVS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13 }}>
          <option value="">All statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
        </select>
        <span style={{ fontSize: 12, color: "#9ca3af", alignSelf: "center" }}>{complaints.length} complaint{complaints.length !== 1 ? "s" : ""}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(400px,1.4fr)", gap: 20, alignItems: "start" }}>
        {/* List */}
        <div style={{ maxHeight: "80vh", overflowY: "auto" }}>
          {complaints.length === 0 && <div style={{ color: "#9ca3af", fontSize: 13, padding: 20, textAlign: "center" }}>No complaints match the current filters.</div>}
          {complaints.map(c => {
            const sla = slaStatus(c.sla_deadline, c.breach_probability);
            return (
              <button key={c.id} onClick={() => onSelect(c.id)}
                style={{ display: "grid", gap: 5, width: "100%", textAlign: "left", padding: 14, marginBottom: 8, background: selected?.id === c.id ? "#eff6ff" : "#fff", border: `1px solid ${selected?.id === c.id ? "#93c5fd" : "#e5e7eb"}`, borderLeft: `4px solid ${sevColor(c.severity)}`, borderRadius: 10, cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <strong style={{ fontSize: 13, color: "#111827" }}>{c.title}</strong>
                  <span style={{ fontSize: 11, color: "#9ca3af", flexShrink: 0, marginLeft: 8 }}>{elapsed(c.created_at)}</span>
                </div>
                <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
                  <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 8, background: sevColor(c.severity), color: "#fff", fontWeight: 700 }}>{c.severity}</span>
                  <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 8, background: statusColor(c.status), color: "#fff", fontWeight: 600 }}>{c.status.replaceAll("_", " ")}</span>
                  <span style={{ fontSize: 11, color: "#6b7280" }}>{catEmoji(c.category)} {c.category.replaceAll("_", " ")}</span>
                  {c.ward_name && <span style={{ fontSize: 11, color: "#9ca3af" }}>{c.ward_name}</span>}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {c.classification_source && (
                    <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 8, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>
                      🤖 {classLabel(c.classification_source)}{c.category_confidence != null ? ` · ${Math.round(c.category_confidence * 100)}%` : ""}
                    </span>
                  )}
                  {c.breach_probability != null && (
                    <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 8, background: c.breach_probability >= 0.6 ? "#fef2f2" : "#f0fdf4", color: c.breach_probability >= 0.6 ? "#b91c1c" : "#15803d", border: `1px solid ${c.breach_probability >= 0.6 ? "#fecaca" : "#bbf7d0"}` }}>
                      {sla.icon} SLA {Math.round(c.breach_probability * 100)}%
                    </span>
                  )}
                  {(c.related_count ?? 0) > 0 && (
                    <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 8, background: "#fef9c3", color: "#854d0e", border: "1px solid #fde68a" }}>
                      ⚠ {c.related_count} related
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Detail */}
        {selected ? (
          <ComplaintDetail
            complaint={selected} workers={workers} workerRecs={workerRecs}
            workerId={workerId} setWorkerId={setWorkerId} loading={loading}
            reclassify={reclassify} verification={verification}
            onStatus={onStatus} onAssign={onAssign}
            onReclassify={onReclassify} onVerify={onVerify}
          />
        ) : (
          <div style={{ padding: 40, textAlign: "center", color: "#9ca3af", fontSize: 13, background: "#fff", borderRadius: 12, border: "1px solid #e5e7eb" }}>
            Select a complaint to view details
          </div>
        )}
      </div>
    </div>
  );
}

// ── Complaint Detail ───────────────────────────────────────────────────────
function ComplaintDetail({ complaint: c, workers, workerRecs, workerId, setWorkerId, loading,
  reclassify, verification, onStatus, onAssign, onReclassify, onVerify }: {
  complaint: Complaint; workers: Worker[]; workerRecs: WorkerRec[];
  workerId: string; setWorkerId: (v: string) => void; loading: boolean;
  reclassify: ClassifyOut | null; verification: VerificationReport | null;
  onStatus: (s: string) => void; onAssign: (id: string) => void;
  onReclassify: () => void; onVerify: () => void;
}) {
  const sla = slaStatus(c.sla_deadline, c.breach_probability);
  const before = c.images?.find(i => i.image_type === "before");
  const after = c.images?.find(i => i.image_type === "after");
  const activeVerif = verification ?? (c.verification_status ? {
    complaint_id: c.id, verified: c.verification_status === "verified",
    status: c.verification_status, composite_score: c.verification_score ?? 0,
    signals: {}, recommendation: "", flags: [], evaluated_at: c.verified_at ?? "", source: "multi_signal_rule_engine",
  } : null);

  return (
    <div style={{ maxHeight: "80vh", overflowY: "auto", display: "grid", gap: 12 }}>
      {/* Header */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#111827" }}>{c.title}</h2>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 8, background: statusColor(c.status), color: "#fff", fontWeight: 700, flexShrink: 0, marginLeft: 8 }}>{c.status.replaceAll("_", " ")}</span>
        </div>
        <p style={{ margin: "0 0 12px", fontSize: 13, color: "#374151", lineHeight: 1.5 }}>{c.description}</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          <MetaRow label="Category" value={<span>{catEmoji(c.category)} {c.category.replaceAll("_", " ")}</span>} />
          <MetaRow label="Severity" value={<Badge label={c.severity} color="#fff" bg={sevColor(c.severity)} />} />
          <MetaRow label="Ward" value={c.ward_name ?? "Not mapped"} />
          <MetaRow label="Assigned to" value={c.assigned_to_name ?? "Unassigned"} />
          <MetaRow label="Submitted" value={fmtDate(c.created_at)} />
          <MetaRow label="SLA" value={<span style={{ color: sla.color, fontWeight: 700 }}>{sla.icon} {sla.label}</span>} />
        </div>
        {c.sla_deadline && (
          <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
            SLA deadline: {fmtTime(c.sla_deadline)}
            {c.escalated_at && <span style={{ color: "#c2410c", marginLeft: 12 }}>⚡ Escalated {fmtTime(c.escalated_at)}</span>}
          </div>
        )}
      </div>

      {/* Priority */}
      {c.priority_score != null && (
        <Section title={`🎯 Priority: ${(c.priority_label ?? "").toUpperCase()} — ${c.priority_score}/100`}>
          {(c.priority_reasons ?? []).length > 0 ? (
            <div style={{ display: "grid", gap: 4 }}>
              {(c.priority_reasons ?? []).map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: "#374151", padding: "3px 0", display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "#1d4ed8" }}>+</span> {r}
                </div>
              ))}
            </div>
          ) : <div style={{ fontSize: 12, color: "#9ca3af" }}>No priority reasons recorded.</div>}
          <Bar pct={c.priority_score} color={c.priority_score >= 80 ? "#b91c1c" : c.priority_score >= 50 ? "#c2410c" : "#b45309"} />
        </Section>
      )}

      {/* Photos */}
      {(before || after) && (
        <Section title="📷 Evidence">
          <div style={{ display: "grid", gridTemplateColumns: before && after ? "1fr 1fr" : "1fr", gap: 10 }}>
            {before && (
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 4, fontWeight: 600 }}>BEFORE</div>
                <img src={`${API}${before.url}`} alt="Before" style={{ width: "100%", maxHeight: 160, objectFit: "cover", borderRadius: 8, border: "1px solid #e5e7eb" }} />
              </div>
            )}
            {after && (
              <div>
                <div style={{ fontSize: 11, color: "#15803d", marginBottom: 4, fontWeight: 600 }}>✓ AFTER</div>
                <img src={`${API}${after.url}`} alt="After" style={{ width: "100%", maxHeight: 160, objectFit: "cover", borderRadius: 8, border: "1px solid #bbf7d0" }} />
              </div>
            )}
          </div>
        </Section>
      )}

      {/* AI Intelligence */}
      <Section title="🤖 AI Intelligence">
        {/* Classification */}
        <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid #f3f4f6" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Classification</span>
            <Btn label={loading ? "Analysing…" : "▶ Re-run Vision AI"} onClick={onReclassify} disabled={loading} variant="primary" />
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
            <strong style={{ fontSize: 14 }}>{(reclassify?.category ?? c.category).replaceAll("_", " ").toUpperCase()}</strong>
            {(reclassify?.confidence ?? c.category_confidence) != null && (
              <Badge label={`${Math.round(((reclassify?.confidence ?? c.category_confidence)!) * 100)}% confidence`} color="#fff" bg="#1d4ed8" />
            )}
            <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 8, background: "#dbeafe", color: "#1e40af", fontWeight: 600 }}>{classLabel(reclassify?.source ?? c.classification_source)}</span>
          </div>
          <ConfBar value={reclassify?.confidence ?? c.category_confidence ?? null} label="Classification confidence" />
          {reclassify?.severity_reason && reclassify.severity_reason.length > 0 && (
            <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>Severity reasons: {reclassify.severity_reason.join(", ")}</div>
          )}
        </div>

        {/* SLA Risk */}
        {c.breach_probability != null && (
          <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid #f3f4f6" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>SLA Breach Risk</span>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6 }}>
              <strong>{Math.round(c.breach_probability * 100)}% breach probability</strong>
              {c.escalation_level && <Badge label={c.escalation_level} color="#fff" bg={escColor(c.escalation_level)} />}
            </div>
            <ConfBar value={c.breach_probability} label="Risk level" dangerAbove={0.6} />
            {c.sla_predicted_at && <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>Predicted {fmtTime(c.sla_predicted_at)}</div>}
          </div>
        )}

        {/* Duplicates */}
        {(c.related_count ?? 0) > 0 && (
          <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid #f3f4f6" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Duplicate Intelligence</span>
            <div style={{ marginTop: 6, padding: 10, background: "#fef9c3", border: "1px solid #fde68a", borderRadius: 8, fontSize: 12 }}>
              ⚠ <strong>{c.related_count} possible duplicate{(c.related_count ?? 0) > 1 ? "s" : ""}</strong> detected nearby with similar text.
              <div style={{ color: "#6b7280", marginTop: 2 }}>Same category · Same area · Recent window</div>
            </div>
          </div>
        )}

        {/* Verification */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Resolution Verification</span>
            <Btn label={loading ? "Verifying…" : "▶ Run Verification"} onClick={onVerify} disabled={loading} variant="primary" />
          </div>
          {activeVerif ? (
            <div style={{ background: "#f9fafb", borderRadius: 8, padding: 10 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <Badge label={activeVerif.status.replaceAll("_", " ")} color="#fff" bg={verColor(activeVerif.status)} />
                <span style={{ fontSize: 13, fontWeight: 700 }}>Score: {Math.round(activeVerif.composite_score * 100)}%</span>
              </div>
              <ConfBar value={activeVerif.composite_score} label="Verification confidence" />
              {activeVerif.recommendation && <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>💬 {activeVerif.recommendation}</div>}
              {activeVerif.flags.length > 0 && <div style={{ fontSize: 12, color: "#b91c1c", marginTop: 4 }}>🚩 {activeVerif.flags.join(" · ")}</div>}
              {Object.keys(activeVerif.signals).length > 0 && (
                <details style={{ marginTop: 8 }}>
                  <summary style={{ cursor: "pointer", fontSize: 12, color: "#4b5563" }}>Signal breakdown</summary>
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {Object.entries(activeVerif.signals).map(([k, v]) => {
                      const sv = v as { passed?: boolean; score?: number; status?: string; details?: string };
                      return (
                        <div key={k} style={{ padding: "4px 8px", background: "#fff", borderRadius: 4, borderLeft: `3px solid ${sv.passed ? "#15803d" : "#b91c1c"}`, fontSize: 12 }}>
                          <span style={{ fontWeight: 600 }}>{k.replaceAll("_", " ")}</span>
                          <span style={{ color: "#6b7280", marginLeft: 8 }}>{sv.passed ? "✓" : "✗"} {sv.status?.replaceAll("_", " ")} · {Math.round((sv.score ?? 0) * 100)}%</span>
                          {sv.details && <div style={{ fontSize: 11, color: "#9ca3af" }}>{sv.details}</div>}
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}
              {c.citizen_rating != null && (
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>
                  ⭐ Citizen rated {c.citizen_rating}/5{c.citizen_feedback ? ` — "${c.citizen_feedback}"` : ""}
                </div>
              )}
            </div>
          ) : <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>No verification run yet. Upload resolution photo first.</div>}
        </div>
      </Section>

      {/* Worker Recommendation */}
      {workerRecs.length > 0 && (
        <Section title="👷 Recommended Workers">
          {workerRecs.map((r, i) => (
            <div key={r.worker_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f9fafb" }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{i === 0 ? "⭐ " : ""}{r.worker_name}</div>
                <div style={{ fontSize: 11, color: "#6b7280" }}>{r.reason}</div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: r.score >= 70 ? "#15803d" : "#b45309" }}>{r.score}pts</span>
                <Btn label="Assign" onClick={() => onAssign(r.worker_id)} variant="success" />
              </div>
            </div>
          ))}
        </Section>
      )}

      {/* Manual assignment */}
      <Section title="⚙️ Actions">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {(c.status === "submitted" || c.status === "reopened") && <Btn label="Start Review" onClick={() => onStatus("under_review")} variant="primary" />}
          {c.status === "under_review" && <Btn label="Reject" onClick={() => onStatus("rejected")} variant="danger" />}
          {c.status === "resolution_submitted" && <Btn label="✓ Verify Resolution" onClick={() => onStatus("verified")} variant="success" />}
        </div>
        {c.status === "under_review" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={workerId} onChange={e => setWorkerId(e.target.value)}
              style={{ padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13, flex: 1 }}>
              <option value="">Select field worker manually</option>
              {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
            <Btn label="Assign" onClick={() => workerId && onAssign(workerId)} disabled={!workerId} variant="primary" />
          </div>
        )}
      </Section>

      {/* Timeline */}
      <Section title="📋 Timeline">
        {(c.timeline ?? []).length === 0 ? <div style={{ fontSize: 12, color: "#9ca3af" }}>No events yet.</div> :
          (c.timeline ?? []).map((ev, i) => (
            <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#9ca3af", marginTop: 5, flexShrink: 0 }} />
              <div>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{ev.action.replaceAll("_", " ")}</span>
                {ev.new_status && <span style={{ fontSize: 12, color: "#6b7280" }}> → {ev.new_status.replaceAll("_", " ")}</span>}
                <div style={{ fontSize: 11, color: "#9ca3af" }}>{fmtTime(ev.timestamp)}</div>
              </div>
            </div>
          ))}
      </Section>
    </div>
  );
}

// ── Assistant Tab ──────────────────────────────────────────────────────────
const SUGGESTED = [
  "Which department has the highest workload?",
  "Which wards have the most complaints?",
  "What are the major unresolved problems in Ward 1?",
  "Generate today's operational summary.",
];

function AssistantTab({ question, setQuestion, answer, loading, onAsk }: {
  question: string; setQuestion: (v: string) => void;
  answer: AssistantAnswer | null; loading: boolean; onAsk: (e: FormEvent) => void;
}) {
  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20, marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Operations Assistant</div>
        <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 16 }}>
          SQL-backed deterministic assistant. All answers come from live database queries — no fabricated statistics.
        </div>
        <form onSubmit={onAsk} style={{ display: "flex", gap: 8 }}>
          <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask an operational question…"
            style={{ flex: 1, padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14 }} />
          <button type="submit" disabled={loading || !question.trim()}
            style={{ padding: "10px 18px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
        <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
          {SUGGESTED.map(q => (
            <button key={q} onClick={() => setQuestion(q)}
              style={{ padding: "4px 10px", borderRadius: 16, border: "1px solid #e5e7eb", background: "#f9fafb", fontSize: 12, cursor: "pointer", color: "#374151" }}>
              {q}
            </button>
          ))}
        </div>
      </div>

      {answer && (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>Q: {answer.question}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#111827", marginBottom: 12 }}>{answer.answer}</div>
          <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 12 }}>Source: SQL rules · Intent: {answer.intent}</div>
          {Object.keys(answer.data).length > 0 && (
            <details>
              <summary style={{ cursor: "pointer", fontSize: 12, color: "#4b5563", marginBottom: 8 }}>View raw data</summary>
              <pre style={{ fontSize: 11, background: "#f9fafb", padding: 12, borderRadius: 8, overflow: "auto", color: "#374151" }}>
                {JSON.stringify(answer.data, null, 2)}
              </pre>
            </details>
          )}
          <details style={{ marginTop: 8 }}>
            <summary style={{ cursor: "pointer", fontSize: 12, color: "#4b5563" }}>Supported questions</summary>
            <ul style={{ marginTop: 8, paddingLeft: 16 }}>
              {answer.supported_questions.map(q => <li key={q} style={{ fontSize: 13, color: "#374151", marginBottom: 4 }}>{q}</li>)}
            </ul>
          </details>
        </div>
      )}
    </div>
  );
}
