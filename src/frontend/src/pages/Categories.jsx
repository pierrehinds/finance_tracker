import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import { api, formatGBP } from "../api";

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

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState(null);
  const [merchants, setMerchants] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .categories()
      .then((data) => {
        const sorted = [...data].sort((a, b) => b.total_spend - a.total_spend);
        setCategories(sorted);
        if (sorted.length > 0) setSelected(sorted[0].category);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.categoryMerchants(selected).then(setMerchants).catch((e) => setError(e.message));
  }, [selected]);

  if (error) return <p style={{ color: "var(--spend)" }}>{error}</p>;
  if (categories.length === 0) return <div style={{ color: "var(--ink-faint)" }}>Loading…</div>;

  return (
    <div>
      <h1 className="page-title">Categories</h1>
      <p className="page-subtitle">Where the money actually goes. Click a bar to see the merchants behind it.</p>

      <div className="card" style={{ padding: "20px 24px", marginBottom: 20 }}>
        <ResponsiveContainer width="100%" height={Math.max(280, categories.length * 30)}>
          <BarChart
            data={categories}
            layout="vertical"
            margin={{ left: 24 }}
            onClick={(state) => {
              const label = state?.activePayload?.[0]?.payload?.category;
              if (label) setSelected(label);
            }}
          >
            <CartesianGrid horizontal={false} stroke="var(--rule)" />
            <XAxis
              type="number"
              tickFormatter={(v) => `£${v}`}
              tick={{ fontSize: 11, fill: "var(--ink-soft)" }}
              axisLine={{ stroke: "var(--rule-strong)" }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="category"
              width={150}
              tick={{ fontSize: 12, fill: "var(--ink)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v) => formatGBP(v)}
              cursor={{ fill: "var(--gold-soft)", opacity: 0.4 }}
              contentStyle={{
                fontSize: 12,
                border: "1px solid var(--rule)",
                borderRadius: 3,
                fontFamily: "var(--font-body)",
              }}
            />
            <Bar dataKey="total_spend" name="Spend" radius={[0, 2, 2, 0]} cursor="pointer">
              {categories.map((entry, i) => (
                <Cell
                  key={entry.category}
                  fill={PALETTE[i % PALETTE.length]}
                  opacity={selected === entry.category ? 1 : 0.55}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: 15, marginBottom: 4 }}>Top merchants — {selected}</h3>
        <p style={{ fontSize: 12, color: "var(--ink-faint)", marginBottom: 16 }}>
          Ranked by total spend within this category
        </p>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--rule)" }}>
              <th style={thStyle}>Merchant / description</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Transactions</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Total spend</th>
            </tr>
          </thead>
          <tbody>
            {merchants.map((m) => (
              <tr key={m.description} style={{ borderBottom: "1px solid var(--rule)" }}>
                <td style={tdStyle}>{m.description}</td>
                <td style={{ ...tdStyle, textAlign: "right" }} className="num">
                  {m.count}
                </td>
                <td style={{ ...tdStyle, textAlign: "right" }} className="num spend">
                  {formatGBP(m.total_spend)}
                </td>
              </tr>
            ))}
            {merchants.length === 0 && (
              <tr>
                <td style={tdStyle} colSpan={3}>
                  No spend transactions in this category.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "8px 6px",
  color: "var(--ink-faint)",
  fontWeight: 500,
  fontSize: 11,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const tdStyle = {
  padding: "9px 6px",
  color: "var(--ink)",
};
