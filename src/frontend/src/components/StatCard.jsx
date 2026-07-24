import { formatGBP } from "../api";

export default function StatCard({ label, value, variant, hint }) {
  const colorClass = variant === "income" ? "income" : variant === "spend" ? "spend" : "";
  return (
    <div className="card" style={{ padding: "18px 20px", flex: 1, minWidth: 160 }}>
      <div
        style={{
          fontSize: 11,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--ink-faint)",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div className={`num ${colorClass}`} style={{ fontSize: 26 }}>
        {formatGBP(value)}
      </div>
      {hint && (
        <div style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 6 }}>{hint}</div>
      )}
    </div>
  );
}
