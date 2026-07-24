import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { api, formatGBP, formatMonth } from "../api";
import StatCard from "../components/StatCard";
import LedgerTape from "../components/LedgerTape";

const PALETTE = [
  "#c08f2a",
  "#2f7a5b",
  "#b54a3c",
  "#4b6f8f",
  "#8b6ba8",
  "#6b8b3a",
  "#9c6b3a",
  "#5a8f8b",
  "#8f5a6f",
  "#7a7a4a",
  "#4a5a7a",
  "#a35a3a",
  "#3a7a6a",
  "#7a3a5a",
  "#5a7a3a",
  "#8b8b8b",
];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [categories, setCategories] = useState([]);
  const [days, setDays] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.summary(), api.monthly(), api.categories(), api.calendar()])
      .then(([s, m, c, d]) => {
        setSummary(s);
        setMonthly(m);
        setCategories(c);
        setDays(d);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!summary) return <div style={{ color: "var(--ink-faint)" }}>Loading…</div>;

  const topCategories = [...categories]
    .filter((c) => c.total_spend > 0)
    .sort((a, b) => b.total_spend - a.total_spend)
    .slice(0, 8);

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        {summary.transaction_count.toLocaleString()} transactions, {summary.date_range.min} to{" "}
        {summary.date_range.max}
        {summary.uncategorised_count > 0 && (
          <> · {summary.uncategorised_count} awaiting categorisation</>
        )}
      </p>

      <div style={{ display: "flex", gap: 14, marginBottom: 20, flexWrap: "wrap" }}>
        <StatCard label="Income" value={summary.total_income} variant="income" />
        <StatCard label="Spend" value={summary.total_spend} variant="spend" />
        <StatCard
          label="Net"
          value={summary.net}
          variant={summary.net >= 0 ? "income" : "spend"}
        />
      </div>

      <div style={{ marginBottom: 20 }}>
        <LedgerTape days={days} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        <div className="card" style={{ padding: "20px 24px" }}>
          <h3 style={{ fontSize: 15, marginBottom: 16 }}>Income vs. spend, by month</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={monthly} margin={{ left: -12 }}>
              <CartesianGrid vertical={false} stroke="var(--rule)" />
              <XAxis
                dataKey="month"
                tickFormatter={formatMonth}
                tick={{ fontSize: 11, fill: "var(--ink-soft)" }}
                axisLine={{ stroke: "var(--rule-strong)" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--ink-soft)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `£${v}`}
              />
              <Tooltip
                formatter={(v) => formatGBP(v)}
                labelFormatter={formatMonth}
                contentStyle={{
                  fontSize: 12,
                  border: "1px solid var(--rule)",
                  borderRadius: 3,
                  fontFamily: "var(--font-body)",
                }}
              />
              <Bar dataKey="total_income" name="Income" fill="var(--income)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="total_spend" name="Spend" fill="var(--spend)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ padding: "20px 24px" }}>
          <h3 style={{ fontSize: 15, marginBottom: 16 }}>Spend by category</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={topCategories}
                dataKey="total_spend"
                nameKey="category"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={1}
                stroke="var(--paper-raised)"
              >
                {topCategories.map((entry, i) => (
                  <Cell key={entry.category} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatGBP(v)} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", marginTop: 4 }}>
            {topCategories.map((c, i) => (
              <div key={c.category} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 2,
                    background: PALETTE[i % PALETTE.length],
                    display: "inline-block",
                  }}
                />
                <span style={{ color: "var(--ink-soft)" }}>{c.category}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p style={{ color: "var(--spend)" }}>
        Couldn't reach the API — is the backend running on port 8000?
        <br />
        <span className="num" style={{ fontSize: 12 }}>
          {message}
        </span>
      </p>
    </div>
  );
}
