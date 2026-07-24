import { useEffect, useMemo, useState } from "react";
import { api, formatGBP } from "../api";

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfWeek(date) {
  const d = new Date(date);
  const day = d.getDay(); // 0 = Sunday
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

export default function CalendarPage() {
  const [days, setDays] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.calendar().then(setDays).catch((e) => setError(e.message));
  }, []);

  const { weeks, months, maxSpend, maxIncome } = useMemo(() => {
    if (days.length === 0) return { weeks: [], months: [], maxSpend: 0, maxIncome: 0 };

    const byDay = new Map(days.map((d) => [d.day, d]));
    const first = startOfWeek(new Date(days[0].day));
    const last = new Date(days[days.length - 1].day);

    const totalDays = Math.ceil((last - first) / DAY_MS) + 7;
    const cells = [];
    for (let i = 0; i < totalDays; i++) {
      const date = new Date(first.getTime() + i * DAY_MS);
      const key = date.toISOString().slice(0, 10);
      cells.push({ date, key, data: byDay.get(key) || null });
    }

    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) {
      weeks.push(cells.slice(i, i + 7));
    }

    const months = [];
    let lastMonth = null;
    weeks.forEach((week, i) => {
      const d = week[0].date;
      const label = d.toLocaleDateString("en-GB", { month: "short" });
      if (label !== lastMonth) {
        months.push({ index: i, label });
        lastMonth = label;
      }
    });

    const maxSpend = Math.max(...days.map((d) => d.total_spend), 1);
    const maxIncome = Math.max(...days.map((d) => d.total_income), 1);

    return { weeks, months, maxSpend, maxIncome };
  }, [days]);

  if (error) return <p style={{ color: "var(--spend)" }}>{error}</p>;
  if (days.length === 0) return <div style={{ color: "var(--ink-faint)" }}>Loading…</div>;

  return (
    <div>
      <h1 className="page-title">Calendar</h1>
      <p className="page-subtitle">Every day, coloured by what happened in it. Click a day for detail.</p>

      <div className="card" style={{ padding: "24px 28px", marginBottom: 20, overflowX: "auto" }}>
        <div style={{ display: "flex", gap: 3, marginBottom: 6, marginLeft: 28 }}>
          {months.map((m) => (
            <div
              key={`${m.label}-${m.index}`}
              style={{
                position: "relative",
                left: m.index * 15,
                fontSize: 11,
                color: "var(--ink-faint)",
                width: 0,
                whiteSpace: "nowrap",
              }}
            >
              {m.label}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 3 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 3, marginRight: 6 }}>
            {["Sun", "", "Tue", "", "Thu", "", "Sat"].map((label, i) => (
              <div
                key={i}
                style={{ height: 12, fontSize: 9, color: "var(--ink-faint)", lineHeight: "12px" }}
              >
                {label}
              </div>
            ))}
          </div>

          {weeks.map((week, wi) => (
            <div key={wi} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {week.map((cell) => (
                <DayCell
                  key={cell.key}
                  cell={cell}
                  maxSpend={maxSpend}
                  maxIncome={maxIncome}
                  onClick={() => cell.data && setSelected(cell.data)}
                  isSelected={selected?.day === cell.key}
                />
              ))}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 16, marginTop: 18, fontSize: 11, color: "var(--ink-faint)" }}>
          <Legend swatch="var(--spend-bg)" label="spend day" />
          <Legend swatch="var(--income-bg)" label="income day" />
          <Legend swatch="var(--rule)" label="no activity" />
        </div>
      </div>

      {selected ? (
        <DayDetail day={selected} />
      ) : (
        <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Select a day above to see its totals.</p>
      )}
    </div>
  );
}

function DayCell({ cell, maxSpend, maxIncome, onClick, isSelected }) {
  const d = cell.data;
  let background = "var(--rule)";
  let title = cell.key;

  if (d) {
    title = `${cell.key} — spend ${formatGBP(d.total_spend)}, income ${formatGBP(d.total_income)}`;
    if (d.net < 0) {
      const intensity = Math.min(1, d.total_spend / maxSpend);
      background = mix("#f6e9e5", "#b54a3c", intensity);
    } else if (d.net > 0) {
      const intensity = Math.min(1, d.total_income / maxIncome);
      background = mix("#e7f1ea", "#2f7a5b", intensity);
    } else {
      background = "var(--rule-strong)";
    }
  }

  return (
    <button
      onClick={onClick}
      title={title}
      className="focus-ring"
      style={{
        width: 12,
        height: 12,
        borderRadius: 2,
        background,
        border: isSelected ? "1.5px solid var(--ink)" : "1px solid transparent",
        padding: 0,
        cursor: d ? "pointer" : "default",
      }}
    />
  );
}

function Legend({ swatch, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 10, height: 10, borderRadius: 2, background: swatch, display: "inline-block" }} />
      {label}
    </div>
  );
}

function DayDetail({ day }) {
  return (
    <div className="card" style={{ padding: "20px 24px" }}>
      <h3 style={{ fontSize: 15, marginBottom: 12 }}>
        {new Date(day.day).toLocaleDateString("en-GB", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        })}
      </h3>
      <div style={{ display: "flex", gap: 28 }}>
        <Stat label="Income" value={day.total_income} variant="income" />
        <Stat label="Spend" value={day.total_spend} variant="spend" />
        <Stat label="Net" value={day.net} variant={day.net >= 0 ? "income" : "spend"} />
        <Stat label="Transactions" value={day.count} raw />
      </div>
    </div>
  );
}

function Stat({ label, value, variant, raw }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--ink-faint)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
      <div className={`num ${variant || ""}`} style={{ fontSize: 18, marginTop: 4 }}>
        {raw ? value : formatGBP(value)}
      </div>
    </div>
  );
}

// simple hex color interpolation
function mix(hexA, hexB, t) {
  const a = hexToRgb(hexA);
  const b = hexToRgb(hexB);
  const r = Math.round(a[0] + (b[0] - a[0]) * t);
  const g = Math.round(a[1] + (b[1] - a[1]) * t);
  const bl = Math.round(a[2] + (b[2] - a[2]) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "");
  const bigint = parseInt(clean, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}
