"""
build_db.py

Collates transaction exports from Monzo, American Express, and Nationwide
into a single SQLite database (via SQLAlchemy), using one unified schema.

Sign convention for `amount`:
    negative = money out (a spend / payment / transfer out)
    positive = money in  (income / refund / transfer in)

Category convention:
    Monzo's own raw categories ARE the canonical category set (`Category` enum
    below). Monzo rows copy their raw category straight across. Amex rows get
    mapped onto the same enum via AmexLoader.CATEGORY_MAP, since Amex uses a
    totally different (and more granular) category scheme. Nationwide provides
    no category at all, so `category` is left NULL for those rows — something
    downstream (rules/LLM) still needs to fill those in.

Everything here is class-based and importable — no argparse, no CLI-only logic.
Typical use, from another script:

    from build_db import FinanceDatabaseBuilder, MonzoLoader, AmexLoader, NationwideLoader

    report = (
        FinanceDatabaseBuilder("transactions.db")
        .add_source(MonzoLoader(), "monzo.csv")
        .add_source(AmexLoader(), "amex.csv")
        .add_source(NationwideLoader(), "nationwide.csv")
        .build()
    )
    report.print_summary()

Running this file directly does exactly that, against the default paths at
the bottom of the file.
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from models.tables import Base, Category, State, Transaction
from sqlalchemy import (
    create_engine,
)
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Loaders — one per bank. Each knows how to parse its own CSV quirks and how
# to map its own category scheme onto the canonical `Category` enum.
# ---------------------------------------------------------------------------


class TransactionLoader(ABC):
    """Base class for a single source's CSV -> list[Transaction] logic."""

    source_name: ClassVar[str]

    @staticmethod
    def parse_money(value: str | None) -> float:
        """Strip £ signs / commas and convert to float. Empty -> 0.0"""
        if value is None:
            return 0.0
        value = value.replace("£", "").replace(",", "").strip()
        if value == "":
            return 0.0
        return float(value)

    @abstractmethod
    def load(self, path: str | Path) -> list[Transaction]:
        """Read the CSV at `path` and return unified Transaction rows."""


class MonzoLoader(TransactionLoader):
    source_name = "monzo"

    def load(self, path: str | Path) -> list[Transaction]:
        path = Path(path)
        rows: list[Transaction] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                date = datetime.strptime(r["Date"], "%d/%m/%Y").date()
                time_val = None
                if r.get("Time"):
                    try:
                        time_val = datetime.strptime(r["Time"], "%H:%M:%S").time()
                    except ValueError:
                        time_val = None

                raw_category = r.get("Category") or None

                rows.append(
                    Transaction(
                        source=self.source_name,
                        source_id=r.get("Transaction ID") or None,
                        date=date,
                        time=time_val,
                        description=r.get("Name") or r.get("Description") or "",
                        amount=self.parse_money(r.get("Amount")),
                        currency=r.get("Currency") or "GBP",
                        balance=None,
                        category_raw=raw_category,
                        category=self._map_category(raw_category),
                        transaction_type=r.get("Type") or None,
                        address=r.get("Address") or None,
                        town_city=None,
                        postcode=None,
                        country=None,
                        notes=r.get("Notes and #tags") or None,
                        extended_details=None,
                    )
                )
        return rows

    def _map_category(self, raw: str | None) -> Category | None:
        """Monzo's raw category IS the canonical category — copy it straight across."""
        if not raw:
            return None
        try:
            return Category(raw)
        except ValueError:
            # A brand-new custom category Monzo hasn't seen before (Monzo lets you
            # type arbitrary category names, like "Arsenal"/"Golf" already in here).
            # Don't crash the whole ingest over it — flag it and leave it NULL.
            print(
                f"  [{self.source_name}] unrecognised category {raw!r} — leaving category NULL"
            )
            return None


class AmexLoader(TransactionLoader):
    source_name = "amex"

    # Amex's raw "Category" values, mapped onto the Monzo-derived Category enum.
    # Amex categories are "Group-Subcategory" strings with no overlap in naming, so
    # this is a manual, judgement-call mapping rather than anything automatic.
    CATEGORY_MAP: ClassVar[dict[str, Category]] = {
        "Business Services-Health Care Services": Category.PERSONAL_CARE,
        "Business Services-Insurance Services": Category.BILLS,
        "Business Services-Office Supplies": Category.EXPENSES,
        "Business Services-Other Services": Category.EXPENSES,
        "Business Services-Printing & Publishing": Category.EXPENSES,
        "Business Services-Professional Services": Category.EXPENSES,
        "Entertainment-Bars & Cafés": Category.EATING_OUT,
        "Entertainment-Clubs": Category.ENTERTAINMENT,
        "Entertainment-Other Entertainment": Category.ENTERTAINMENT,
        "Entertainment-Restaurants": Category.EATING_OUT,
        "Entertainment-Theatrical Events": Category.ENTERTAINMENT,
        "General Purchases-Book Stores": Category.SHOPPING,
        "General Purchases-Clothing Stores": Category.SHOPPING,
        "General Purchases-Computer Supplies": Category.SHOPPING,
        "General Purchases-Department Stores": Category.SHOPPING,
        "General Purchases-Fuel": Category.TRANSPORT,
        "General Purchases-Furnishing": Category.SHOPPING,
        "General Purchases-General Retail": Category.SHOPPING,
        "General Purchases-Groceries": Category.GROCERIES,
        "General Purchases-Mail Order": Category.SHOPPING,
        "General Purchases-Music & Video": Category.ENTERTAINMENT,
        "General Purchases-Online Purchases": Category.SHOPPING,
        "General Purchases-Parking Charges": Category.TRANSPORT,
        "General Purchases-Pharmacies": Category.PERSONAL_CARE,
        "General Purchases-Sporting Goods Stores": Category.SHOPPING,
        "Travel-Airline": Category.HOLIDAYS,
        "Travel-Other Travel": Category.HOLIDAYS,
        "Travel-Rail Services": Category.TRANSPORT,  # ambiguous: commute vs. trip
        "Travel-Taxis & Coach": Category.TRANSPORT,
    }

    def load(self, path: str | Path) -> list[Transaction]:
        path = Path(path)
        rows: list[Transaction] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                date = datetime.strptime(r["Date"], "%d/%m/%Y").date()
                # Amex convention is the opposite of the unified one:
                # positive = spend, negative = payment/credit received.
                # Flip the sign so negative = spend everywhere.
                amount = -self.parse_money(r.get("Amount"))

                raw_category = r.get("Category") or None

                rows.append(
                    Transaction(
                        source=self.source_name,
                        source_id=(r.get("Reference") or "").strip("'") or None,
                        date=date,
                        time=None,
                        description=r.get("Description") or "",
                        amount=amount,
                        currency="GBP",
                        balance=None,
                        category_raw=raw_category,
                        category=self._map_category(raw_category),
                        transaction_type=r.get("Appears On Your Statement As") or None,
                        address=r.get("Address") or None,
                        town_city=r.get("Town/City") or None,
                        postcode=r.get("Postcode") or None,
                        country=r.get("Country") or None,
                        notes=None,
                        extended_details=r.get("Extended Details") or None,
                    )
                )
        return rows

    def _map_category(self, raw: str | None) -> Category | None:
        if not raw:
            return None
        mapped = self.CATEGORY_MAP.get(raw)
        if mapped is None:
            print(
                f"  [{self.source_name}] no mapping for category {raw!r} — leaving category NULL"
            )
        return mapped


class NationwideLoader(TransactionLoader):
    source_name = "nationwide"

    def load(self, path: str | Path) -> list[Transaction]:
        path = Path(path)
        with open(path, newline="", encoding="utf-8-sig") as f:
            lines = f.readlines()

        # Nationwide exports have preamble rows (account name/balance) before
        # the real header. Find the row that actually looks like the header.
        header_idx = None
        for i, line in enumerate(lines):
            if line.startswith('"Date"'):
                header_idx = i
                break
        if header_idx is None:
            raise ValueError("Could not find Nationwide CSV header row")

        rows: list[Transaction] = []
        reader = csv.DictReader(lines[header_idx:])
        for r in reader:
            if not r.get("Date"):
                continue
            date = datetime.strptime(r["Date"], "%d %b %Y").date()

            paid_out = self.parse_money(r.get("Paid out"))
            paid_in = self.parse_money(r.get("Paid in"))
            amount = paid_in - paid_out  # negative if money went out

            balance_raw = r.get("Balance")
            balance = self.parse_money(balance_raw) if balance_raw else None

            rows.append(
                Transaction(
                    source=self.source_name,
                    source_id=None,  # Nationwide doesn't provide a per-transaction ID
                    date=date,
                    time=None,
                    description=r.get("Description") or "",
                    amount=amount,
                    currency="GBP",
                    balance=balance,
                    category_raw=None,  # Nationwide doesn't categorise
                    category=None,  # nothing to map from — needs rules/LLM downstream
                    transaction_type=r.get("Transaction type") or None,
                    address=None,  # Nationwide doesn't provide location fields
                    town_city=None,
                    postcode=None,
                    country=None,
                    notes=None,
                    extended_details=None,
                )
            )
        return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


@dataclass
class BuildReport:
    db_path: Path
    total: int = 0
    per_source: dict[str, int] = field(default_factory=dict)
    per_source_categorised: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, db_path: Path, rows: list[Transaction]) -> BuildReport:
        report = cls(db_path=db_path, total=len(rows))
        for row in rows:
            report.per_source[row.source] = report.per_source.get(row.source, 0) + 1
            if row.category is not None:
                report.per_source_categorised[row.source] = (
                    report.per_source_categorised.get(row.source, 0) + 1
                )
        return report

    def print_summary(self) -> None:
        print(f"Wrote {self.total} transactions to {self.db_path}")
        for source, n in self.per_source.items():
            categorised = self.per_source_categorised.get(source, 0)
            print(f"  {source}: {n} ({categorised} categorised)")


# ---------------------------------------------------------------------------
# Builder — owns the engine/session, wires loaders to their CSV paths, writes
# everything to a fresh SQLite file.
# ---------------------------------------------------------------------------


class FinanceDatabaseBuilder:
    """
    Usage:
        report = (
            FinanceDatabaseBuilder("transactions.db")
            .add_source(MonzoLoader(), "monzo.csv")
            .add_source(AmexLoader(), "amex.csv")
            .add_source(NationwideLoader(), "nationwide.csv")
            .build()
        )
    """

    def __init__(self, db_path: str | Path, fresh: bool = True):
        self.db_path = Path(db_path)
        self.fresh = fresh
        self._sources: list[tuple[TransactionLoader, Path]] = []

    def add_source(
        self, loader: TransactionLoader, path: str | Path
    ) -> FinanceDatabaseBuilder:
        """Register a loader + its CSV path. Chainable."""
        self._sources.append((loader, Path(path)))
        return self

    def build(self) -> BuildReport:
        if self.fresh and self.db_path.exists():
            self.db_path.unlink()  # start fresh each run

        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        all_rows: list[Transaction] = []
        for loader, path in self._sources:
            all_rows.extend(loader.load(path))

        if not all_rows:
            raise ValueError("No transactions were loaded from any registered source.")

        session.add_all(all_rows)
        session.add(State(last_entry_date=max(r.date for r in all_rows)))
        session.commit()

        report = BuildReport.from_rows(self.db_path, all_rows)
        session.close()
        return report


if __name__ == "__main__":
    report = (
        FinanceDatabaseBuilder("src/data/transactions.db")
        .add_source(MonzoLoader(), "src/data/raw/monzo.csv")
        .add_source(AmexLoader(), "src/data/raw/amex.csv")
        .add_source(NationwideLoader(), "src/data/raw/nationwide.csv")
        .build()
    )
    report.print_summary()
