from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Date,
    Float,
    Integer,
    String,
    Time,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Category(str, Enum):
    """Canonical category set — taken verbatim from Monzo's own raw categories."""

    ARSENAL = "Arsenal"
    BILLS = "Bills"
    EATING_OUT = "Eating out"
    ENTERTAINMENT = "Entertainment"
    EXPENSES = "Expenses"
    FINANCES = "Finances"
    GENERAL = "General"
    GIFTS = "Gifts"
    GOLF = "Golf"
    GROCERIES = "Groceries"
    HOLIDAYS = "Holidays"
    MONEY_OWED = "Money Owed"
    MONTHLY_PAYMENTS = "Monthly Payments"
    PERSONAL_CARE = "Personal care"
    SHOPPING = "Shopping"
    TRANSFERS = "Transfers"
    TRANSPORT = "Transport"


class Transaction(Base):
    """
    Unified transaction record. Fields that overlap across banks
    (e.g. address, which both Monzo and Amex provide) share a single
    column; fields a given bank doesn't provide are left NULL for
    rows from that source.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Provenance
    source = Column(String, nullable=False)  # 'monzo' | 'amex' | 'nationwide'
    source_id = Column(String, nullable=True)  # Monzo Transaction ID / Amex Reference

    # When
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=True)  # only Monzo provides a time

    # What / how much
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # negative = spend, positive = income
    currency = Column(String, nullable=True, default="GBP")
    balance = Column(Float, nullable=True)  # running balance, Nationwide only

    # Categorisation
    category_raw = Column(String, nullable=True)  # untouched, as given by the source
    category = Column(
        SAEnum(Category, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=True,
    )
    transaction_type = Column(
        String, nullable=True
    )  # Monzo 'Type' / Nationwide 'Transaction type'

    # Location (overlap: Monzo + Amex both have address)
    address = Column(String, nullable=True)
    town_city = Column(String, nullable=True)
    postcode = Column(String, nullable=True)
    country = Column(String, nullable=True)

    # Misc extras that don't fit elsewhere
    notes = Column(String, nullable=True)  # Monzo 'Notes and #tags'
    extended_details = Column(String, nullable=True)  # Amex 'Extended Details'

    def __repr__(self):
        return (
            f"<Transaction {self.source} {self.date} "
            f"{self.amount:+.2f} {self.description!r}>"
        )


class State(Base):
    """Key-value store for persistent state, e.g. last processed date."""

    __tablename__ = "state"

    id = Column(Integer, primary_key=True, default=1)
    last_update = Column(Date, default=datetime.now())
    date_classified_upto = Column(Date, nullable=True)
    last_entry_date = Column(Date, nullable=False)
