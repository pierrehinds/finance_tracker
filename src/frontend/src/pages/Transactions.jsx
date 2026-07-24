import { useEffect, useState } from "react";
import { api, formatGBP } from "../api";

const PAGE_SIZE = 25;

export default function Transactions() {
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [source, setSource] = useState("");
  const [sort, setSort] = useState("date_desc");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [search, category, source, sort]);

  useEffect(() => {
    const handle = setTimeout(() => {
      api
        .transactions({ page, page_size: PAGE_SIZE, search, category, source, sort })
        .then(setData)
        .catch((e) => setError(e.message));
    }, 200); // debounce search typing
    return () => clearTimeout(handle);
  }, [page, search, category, source, sort]);

  if (error) return <p style={{ color: "var(--spend)" }}>{error}</p>;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <h1 className="page-title">Transactions</h1>
      <p className="page-subtitle">Search and filter across all three accounts.</p>

      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 18,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <input
          className="focus-ring"
          placeholder="Search description, merchant, address…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={inputStyle({ minWidth: 260, flex: 1 })}
        />
        <select
          className="focus-ring"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          style={inputStyle({})}
        >
          <option value="">All categories</option>
          {meta?.categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
          <option value="Uncategorised">Uncategorised</option>
        </select>
        <select
          className="focus-ring"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          style={inputStyle({})}
        >
          <option value="">All sources</option>
          {meta?.sources.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          className="focus-ring"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          style={inputStyle({})}
        >
          <option value="date_desc">Newest first</option>
          <option value="date_asc">Oldest first</option>
          <option value="amount_desc">Largest amount</option>
          <option value="amount_asc">Smallest amount</option>
        </select>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--rule)", background: "var(--paper)" }}>
              <th style={thStyle}>Date</th>
              <th style={thStyle}>Description</th>
              <th style={thStyle}>Category</th>
              <th style={thStyle}>Source</th>
              <th style={{ ...thStyle, textAlign: "right" }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((t) => (
              <tr key={t.id} style={{ borderBottom: "1px solid var(--rule)" }}>
                <td style={tdStyle}>{t.date}</td>
                <td style={{ ...tdStyle, maxWidth: 320 }}>{t.description}</td>
                <td style={tdStyle}>
                  {t.category ? (
                    <span
                      style={{
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 10,
                        background: "var(--gold-soft)",
                        color: "var(--ink)",
                      }}
                    >
                      {t.category}
                    </span>
                  ) : (
                    <span style={{ fontSize: 11, color: "var(--ink-faint)" }}>—</span>
                  )}
                </td>
                <td style={{ ...tdStyle, textTransform: "capitalize", color: "var(--ink-soft)" }}>
                  {t.source}
                </td>
                <td
                  style={{ ...tdStyle, textAlign: "right" }}
                  className={`num ${t.amount < 0 ? "spend" : "income"}`}
                >
                  {t.amount < 0 ? "−" : "+"}
                  {formatGBP(Math.abs(t.amount))}
                </td>
              </tr>
            ))}
            {data && data.results.length === 0 && (
              <tr>
                <td style={tdStyle} colSpan={5}>
                  No transactions match those filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 14,
            fontSize: 13,
            color: "var(--ink-soft)",
          }}
        >
          <span>
            {data.total.toLocaleString()} result{data.total === 1 ? "" : "s"}
          </span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button
              className="focus-ring"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={pageBtnStyle}
            >
              Prev
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              className="focus-ring"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              style={pageBtnStyle}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function inputStyle(extra) {
  return {
    padding: "9px 12px",
    border: "1px solid var(--rule-strong)",
    borderRadius: 3,
    background: "var(--paper-raised)",
    fontSize: 13,
    color: "var(--ink)",
    ...extra,
  };
}

const pageBtnStyle = {
  padding: "6px 12px",
  border: "1px solid var(--rule-strong)",
  borderRadius: 3,
  background: "var(--paper-raised)",
  cursor: "pointer",
  fontSize: 13,
};

const thStyle = {
  textAlign: "left",
  padding: "10px 12px",
  color: "var(--ink-faint)",
  fontWeight: 500,
  fontSize: 11,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const tdStyle = {
  padding: "10px 12px",
  color: "var(--ink)",
};
