"""
FastAPI backend for the personal finance dashboard.

Serves data out of transactions.db (built by build_db.py / classify_transactions.py)
to the React frontend.

Run:
    export DB_PATH=transactions.db   # optional, this is the default
    uvicorn main:app --reload --port 8000
"""

import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import MetaData, Table, and_, case, create_engine, func, or_, select

DB_PATH = os.environ.get(
    "/Users/pierrehinds/Documents/Repos/FinanceTracker/src/data/transactions.db",
    "transactions.db",
)

engine = create_engine(f"sqlite:///{DB_PATH}")
metadata = MetaData()
transactions = Table("transactions", metadata, autoload_with=engine)

app = FastAPI(title="Personal Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- helpers ----------


def date_filters(start: Optional[date], end: Optional[date]):
    conds = []
    if start:
        conds.append(transactions.c.date >= start)
    if end:
        conds.append(transactions.c.date <= end)
    return conds


# ---------- schemas ----------


class Transaction(BaseModel):
    id: int
    source: str
    source_id: Optional[str] = None
    date: date
    time: Optional[str] = None
    description: str
    amount: float
    currency: Optional[str] = None
    balance: Optional[float] = None
    category_raw: Optional[str] = None
    transaction_type: Optional[str] = None
    address: Optional[str] = None
    town_city: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    extended_details: Optional[str] = None
    classified_at: Optional[str] = None


class TransactionPage(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[Transaction]


class CategoryTotal(BaseModel):
    category: str
    total_spend: float
    total_income: float
    count: int


class MonthTotal(BaseModel):
    month: str  # YYYY-MM
    total_spend: float
    total_income: float
    net: float


class DayTotal(BaseModel):
    day: str  # YYYY-MM-DD
    total_spend: float
    total_income: float
    net: float
    count: int


class Summary(BaseModel):
    total_income: float
    total_spend: float
    net: float
    transaction_count: int
    uncategorised_count: int
    date_range: dict


class Merchant(BaseModel):
    description: str
    total_spend: float
    count: int


class Meta(BaseModel):
    min_date: Optional[date]
    max_date: Optional[date]
    sources: list[str]
    categories: list[str]


# ---------- routes ----------


@app.get("/api/meta", response_model=Meta)
def get_meta():
    with engine.connect() as conn:
        min_date, max_date = conn.execute(
            select(func.min(transactions.c.date), func.max(transactions.c.date))
        ).one()
        sources = [r[0] for r in conn.execute(select(transactions.c.source).distinct())]
        categories = [
            r[0]
            for r in conn.execute(
                select(transactions.c.category)
                .where(transactions.c.category.is_not(None))
                .distinct()
            )
        ]
    return Meta(
        min_date=min_date,
        max_date=max_date,
        sources=sorted(sources),
        categories=sorted(categories),
    )


@app.get("/api/summary", response_model=Summary)
def get_summary(start: Optional[date] = None, end: Optional[date] = None):
    conds = date_filters(start, end)
    with engine.connect() as conn:
        row = conn.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (transactions.c.amount > 0, transactions.c.amount), else_=0
                        )
                    ),
                    0.0,
                ).label("income"),
                func.coalesce(
                    func.sum(
                        case(
                            (transactions.c.amount < 0, -transactions.c.amount), else_=0
                        )
                    ),
                    0.0,
                ).label("spend"),
                func.count().label("count"),
            ).where(and_(*conds) if conds else True)
        ).one()

        uncategorised = conn.execute(
            select(func.count()).where(and_(transactions.c.category.is_(None), *conds))
        ).scalar()

        min_date, max_date = conn.execute(
            select(func.min(transactions.c.date), func.max(transactions.c.date)).where(
                and_(*conds) if conds else True
            )
        ).one()

    return Summary(
        total_income=row.income,
        total_spend=row.spend,
        net=row.income - row.spend,
        transaction_count=row.count,
        uncategorised_count=uncategorised or 0,
        date_range={"min": min_date, "max": max_date},
    )


@app.get("/api/categories", response_model=list[CategoryTotal])
def get_categories(start: Optional[date] = None, end: Optional[date] = None):
    conds = date_filters(start, end)
    query = (
        select(
            func.coalesce(transactions.c.category, "Uncategorised").label("category"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount < 0, -transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_spend"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount > 0, transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_income"),
            func.count().label("count"),
        )
        .where(and_(*conds) if conds else True)
        .group_by("category")
        .order_by(
            func.sum(
                case((transactions.c.amount < 0, -transactions.c.amount), else_=0)
            ).desc()
        )
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [
        CategoryTotal(
            category=r.category,
            total_spend=r.total_spend,
            total_income=r.total_income,
            count=r.count,
        )
        for r in rows
    ]


@app.get("/api/monthly", response_model=list[MonthTotal])
def get_monthly(start: Optional[date] = None, end: Optional[date] = None):
    conds = date_filters(start, end)
    month_expr = func.strftime("%Y-%m", transactions.c.date)
    query = (
        select(
            month_expr.label("month"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount < 0, -transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_spend"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount > 0, transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_income"),
        )
        .where(and_(*conds) if conds else True)
        .group_by("month")
        .order_by("month")
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [
        MonthTotal(
            month=r.month,
            total_spend=r.total_spend,
            total_income=r.total_income,
            net=r.total_income - r.total_spend,
        )
        for r in rows
    ]


@app.get("/api/calendar", response_model=list[DayTotal])
def get_calendar(start: Optional[date] = None, end: Optional[date] = None):
    conds = date_filters(start, end)
    query = (
        select(
            transactions.c.date.label("day"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount < 0, -transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_spend"),
            func.coalesce(
                func.sum(
                    case((transactions.c.amount > 0, transactions.c.amount), else_=0)
                ),
                0.0,
            ).label("total_income"),
            func.count().label("count"),
        )
        .where(and_(*conds) if conds else True)
        .group_by(transactions.c.date)
        .order_by(transactions.c.date)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [
        DayTotal(
            day=str(r.day),
            total_spend=r.total_spend,
            total_income=r.total_income,
            net=r.total_income - r.total_spend,
            count=r.count,
        )
        for r in rows
    ]


@app.get("/api/categories/{category}/merchants", response_model=list[Merchant])
def get_category_merchants(category: str, limit: int = 15):
    cat_filter = (
        transactions.c.category.is_(None)
        if category == "Uncategorised"
        else transactions.c.category == category
    )
    query = (
        select(
            transactions.c.description,
            func.sum(-transactions.c.amount).label("total_spend"),
            func.count().label("count"),
        )
        .where(and_(cat_filter, transactions.c.amount < 0))
        .group_by(transactions.c.description)
        .order_by(func.sum(-transactions.c.amount).desc())
        .limit(limit)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [
        Merchant(description=r.description, total_spend=r.total_spend, count=r.count)
        for r in rows
    ]


@app.get("/api/transactions", response_model=TransactionPage)
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    sort: str = "date_desc",
):
    conds = date_filters(start, end)

    if category:
        conds.append(
            transactions.c.category.is_(None)
            if category == "Uncategorised"
            else transactions.c.category == category
        )
    if source:
        conds.append(transactions.c.source == source)
    if search:
        like = f"%{search}%"
        conds.append(
            or_(
                transactions.c.description.ilike(like),
                transactions.c.category_raw.ilike(like),
                transactions.c.address.ilike(like),
            )
        )

    where_clause = and_(*conds) if conds else True

    sort_map = {
        "date_desc": transactions.c.date.desc(),
        "date_asc": transactions.c.date.asc(),
        "amount_desc": transactions.c.amount.desc(),
        "amount_asc": transactions.c.amount.asc(),
    }
    order_by = sort_map.get(sort, transactions.c.date.desc())

    with engine.connect() as conn:
        total = conn.execute(select(func.count()).where(where_clause)).scalar()
        rows = conn.execute(
            select(transactions)
            .where(where_clause)
            .order_by(order_by, transactions.c.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()

    return TransactionPage(
        total=total,
        page=page,
        page_size=page_size,
        results=[Transaction(**r._mapping) for r in rows],
    )


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            select(transactions).where(transactions.c.id == transaction_id)
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Transaction(**row._mapping)


@app.get("/api/health")
def health():
    return {"status": "ok", "db_path": DB_PATH}
