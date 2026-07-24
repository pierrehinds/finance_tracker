const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, params = {}) {
  const url = new URL(BASE_URL + path);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  meta: () => request("/api/meta"),
  summary: (params) => request("/api/summary", params),
  categories: (params) => request("/api/categories", params),
  monthly: (params) => request("/api/monthly", params),
  calendar: (params) => request("/api/calendar", params),
  categoryMerchants: (category, params) =>
    request(`/api/categories/${encodeURIComponent(category)}/merchants`, params),
  transactions: (params) => request("/api/transactions", params),
  transaction: (id) => request(`/api/transactions/${id}`),
};

export function formatGBP(value) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatMonth(monthStr) {
  const [year, month] = monthStr.split("-");
  const d = new Date(Number(year), Number(month) - 1, 1);
  return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
}
