import { useMemo } from "react";
import { formatGBP } from "../api";

/**
 * A running-balance strip styled like adding-machine paper tape.
 * Takes the daily {day, net} series and draws a cumulative balance line,
 * with a perforated edge to nod at the "ledger" subject matter.
 */
export default function LedgerTape({ days }) {
  const { points, path, min, max, last, width, height } = useMemo(() => {
    const width = 1000;
    const height = 110;
    const pad = 8;

    if (!days || days.length === 0) {
      return { points: [], path: "", min: 0, max: 0, last: 0, width, height };
    }

    let running = 0;
    const cumulative = days.map((d) => {
      running += d.net;
      return running;
    });

    const min = Math.min(...cumulative, 0);
    const max = Math.max(...cumulative, 0);
    const range = max - min || 1;

    const points = cumulative.map((v, i) => {
      const x = (i / (cumulative.length - 1 || 1)) * (width - pad * 2) + pad;
      const y = height - pad - ((v - min) / range) * (height - pad * 2);
      return [x, y];
    });

    const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

    return { points, path, min, max, last: cumulative[cumulative.length - 1], width, height };
  }, [days]);

  if (!days || days.length === 0) return null;

  return (
    <div
      className="card"
      style={{
        padding: "18px 20px 22px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 6,
        }}
      >
        <div
          style={{
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--ink-faint)",
          }}
        >
          Running balance, net of the period
        </div>
        <div className={`num ${last >= 0 ? "income" : "spend"}`} style={{ fontSize: 15 }}>
          {formatGBP(last)}
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none">
        <line
          x1="0"
          x2={width}
          y1={height - 8 - ((0 - min) / (max - min || 1)) * (height - 16)}
          y2={height - 8 - ((0 - min) / (max - min || 1)) * (height - 16)}
          stroke="var(--rule-strong)"
          strokeDasharray="2 3"
          strokeWidth="1"
        />
        <path d={path} fill="none" stroke="var(--gold)" strokeWidth="2" />
        {points.length > 0 && (
          <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r="3.5" fill="var(--ink)" />
        )}
      </svg>

      {/* perforated tear edge, a nod to receipt/ledger paper */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 6,
          backgroundImage:
            "radial-gradient(circle at 6px 0px, var(--paper) 3px, transparent 3.5px)",
          backgroundSize: "12px 6px",
          backgroundRepeat: "repeat-x",
        }}
      />
    </div>
  );
}
