import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/transactions", label: "Transactions" },
  { to: "/categories", label: "Categories" },
  { to: "/calendar", label: "Calendar" },
];

export default function Sidebar() {
  return (
    <aside
      style={{
        borderRight: "1px solid var(--rule)",
        padding: "28px 24px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ marginBottom: 32 }}>
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "-0.01em",
          }}
        >
          Ledger
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 2 }}>
          personal accounts
        </div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className="focus-ring"
            style={({ isActive }) => ({
              padding: "9px 12px",
              borderRadius: 3,
              textDecoration: "none",
              fontSize: 14,
              color: isActive ? "var(--ink)" : "var(--ink-soft)",
              background: isActive ? "var(--gold-soft)" : "transparent",
              fontWeight: isActive ? 600 : 500,
              transition: "background 120ms ease, color 120ms ease",
            })}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div
        style={{
          marginTop: "auto",
          paddingTop: 24,
          fontSize: 11,
          color: "var(--ink-faint)",
          lineHeight: 1.5,
        }}
      >
        Monzo · Amex · Nationwide
        <br />
        consolidated locally
      </div>
    </aside>
  );
}
