import datetime

from pydantic import BaseModel


class Transaction(BaseModel):
    source: str
    source_id: str | None = None
    date: datetime.date
    time: datetime.time | None = None
    description: str
    amount: float
    currency: str | None = None
    balance: float | None = None
    category_raw: str | None = None
    transaction_type: str | None = None
    address: str | None = None
    town_city: str | None = None
    postcode: str | None = None
    country: str | None = None
    notes: str | None = None
    extended_details: str | None = None
    classified_at: str | None = None


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
    min_date: datetime.date | None
    max_date: datetime.date | None
    sources: list[str]
    categories: list[str]
