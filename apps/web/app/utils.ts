export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const headers: Record<string, string> = isForm
    ? { Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers as Record<string, string> | undefined) };
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as T;
}

export function severityColor(s: string): string {
  const m: Record<string, string> = { CRITICAL: "#b91c1c", HIGH: "#c2410c", MEDIUM: "#b45309", LOW: "#15803d" };
  return m[s?.toUpperCase()] ?? "#4b5563";
}

export function statusColor(s: string): string {
  const m: Record<string, string> = {
    submitted: "#1d4ed8", under_review: "#7c3aed", assigned: "#0891b2",
    in_progress: "#d97706", resolution_submitted: "#059669",
    verified: "#15803d", closed: "#374151", rejected: "#b91c1c", reopened: "#c2410c",
  };
  return m[s] ?? "#6b7280";
}

export function verificationColor(s: string | null | undefined): string {
  if (!s) return "#6b7280";
  const m: Record<string, string> = {
    verified: "#15803d", provisionally_verified: "#ca8a04",
    needs_review: "#b45309", unverified: "#b91c1c", pending: "#6b7280", citizen_rejected: "#b91c1c",
  };
  return m[s] ?? "#6b7280";
}

export function escalationColor(l: string | null | undefined): string {
  if (!l) return "#6b7280";
  const m: Record<string, string> = { none: "#15803d", watch: "#ca8a04", escalate: "#c2410c", critical: "#b91c1c" };
  return m[l] ?? "#6b7280";
}

export function classLabel(src: string | null | undefined): string {
  if (!src) return "Unknown";
  if (src === "vision_mobilenet_v3") return "Vision AI";
  if (src.startsWith("sklearn_text")) return "Text ML";
  if (src === "demo_classifier") return "Keyword";
  return src;
}

export function categoryEmoji(cat: string): string {
  const m: Record<string, string> = {
    garbage: "🗑️", pothole: "🕳️", drainage: "🌊",
    streetlight: "💡", water_leakage: "💧", other: "📋",
  };
  return m[cat] ?? "📋";
}

export const CATEGORIES = ["garbage", "pothole", "drainage", "streetlight", "water_leakage", "other"];

export const S = {
  shell: { maxWidth: 1400, margin: "0 auto", padding: "24px 20px", fontFamily: "'Inter','Segoe UI',Arial,sans-serif", color: "#111827", background: "#f8fafc", minHeight: "100vh" },
  topbar: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, padding: "16px 20px", background: "#fff", borderRadius: 12, border: "1px solid #e5e7eb", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginBottom: 24 },
  kpi: { padding: "16px 18px", background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, display: "grid", gap: 4, boxShadow: "0 1px 2px rgba(0,0,0,0.04)" },
  kpiLabel: { fontSize: 11, color: "#6b7280", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.05em" },
  kpiValue: { fontSize: 26, fontWeight: 700, color: "#111827" },
  grid2: { display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(360px,1.3fr)", gap: 20, alignItems: "start" },
  panel: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 18, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  panelTitle: { fontSize: 14, fontWeight: 700, color: "#111827", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 },
  badge: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 700 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, background: "#f3f4f6", color: "#374151" },
  btn: { padding: "8px 14px", borderRadius: 8, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#374151" },
  btnPrimary: { padding: "8px 14px", borderRadius: 8, border: "none", background: "#1d4ed8", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#fff" },
  btnDanger: { padding: "8px 14px", borderRadius: 8, border: "none", background: "#fef2f2", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#b91c1c" },
  btnSuccess: { padding: "8px 14px", borderRadius: 8, border: "none", background: "#f0fdf4", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#15803d" },
  input: { padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13, width: "100%", boxSizing: "border-box" as const },
  select: { padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 13 },
  error: { color: "#b91c1c", fontSize: 13, padding: "8px 12px", background: "#fef2f2", borderRadius: 8, marginBottom: 12 },
  tag: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", fontWeight: 600 },
  metaRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: "1px solid #f3f4f6", fontSize: 13 },
  timelineDot: { width: 8, height: 8, borderRadius: "50%", background: "#9ca3af", marginTop: 5, flexShrink: 0 },
  crisisCritical: { background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10, padding: 14, marginBottom: 10 },
  crisisWarning: { background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 14, marginBottom: 10 },
  filterBar: { display: "flex", gap: 6, flexWrap: "wrap" as const, marginBottom: 12 },
  filterBtn: (active: boolean) => ({ padding: "5px 12px", borderRadius: 16, border: `1px solid ${active ? "#1d4ed8" : "#d1d5db"}`, background: active ? "#eff6ff" : "#fff", color: active ? "#1d4ed8" : "#374151", cursor: "pointer", fontSize: 12, fontWeight: 600 }),
  complaintCard: (selected: boolean, severity: string) => ({
    display: "grid", gap: 5, width: "100%", textAlign: "left" as const,
    padding: 14, marginBottom: 8, background: selected ? "#f0f7ff" : "#fff",
    border: `1px solid ${selected ? "#93c5fd" : "#e5e7eb"}`,
    borderLeft: `4px solid ${severityColor(severity)}`,
    borderRadius: 10, cursor: "pointer",
  }),
};
