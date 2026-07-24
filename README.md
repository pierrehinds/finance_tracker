# Personal finance dashboard

A local FastAPI backend + React (Vite) frontend for browsing the
`transactions.db` produced by `build_db.py` / `classify_transactions.py`.

## 1. Backend

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # drop the flag if not needed on your machine
export DB_PATH=/path/to/transactions.db   # optional, defaults to ./transactions.db
uvicorn main:app --reload --port 8000
```

Check it's up: http://localhost:8000/api/health

Endpoints:
- `GET /api/meta` — date range, list of sources, list of categories (for filter dropdowns)
- `GET /api/summary?start=&end=` — total income/spend/net for a period
- `GET /api/categories?start=&end=` — totals per category
- `GET /api/categories/{category}/merchants` — top merchants within a category
- `GET /api/monthly?start=&end=` — monthly income/spend/net series
- `GET /api/calendar?start=&end=` — daily income/spend/net series (for the heatmap)
- `GET /api/transactions?page=&page_size=&search=&category=&source=&start=&end=&sort=` — paginated, filterable transaction list
- `GET /api/transactions/{id}` — single transaction

All `date` params are `YYYY-MM-DD`. `sort` is one of `date_desc` (default), `date_asc`, `amount_desc`, `amount_asc`.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — it talks to the backend at `http://localhost:8000` by default.
Override with a `.env` file in `frontend/`:

```
VITE_API_URL=http://localhost:8000
```

### Pages

- **Dashboard** — income/spend/net totals, a running-balance "ledger tape", monthly income vs. spend bars, category pie chart
- **Transactions** — searchable, filterable (category/source/date), sortable, paginated table
- **Categories** — spend-by-category bar chart; click a bar to see the top merchants driving that category
- **Calendar** — a GitHub-style daily heatmap (green = net income day, red = net spend day); click a day for its totals

Everything is plain React + `recharts` + hand-rolled SVG (the ledger tape and calendar heatmap) — no component library, so it's easy to pull apart and extend. `src/api.js` has all the fetch calls in one place if you want to add more endpoints or pages.

## Notes / things you'll likely want to change

- `transactions.db` included here is a snapshot at time of writing — regenerate it with `build_db.py` and re-classify with `classify_transactions.py` as you add new exports.
- The backend re-derives everything from SQL on each request rather than caching; fine at this data volume (~1k rows), worth revisiting if it grows a lot.
- CORS is currently locked to `localhost:5173` in `backend/main.py` — update `allow_origins` if you serve the frontend from somewhere else.
