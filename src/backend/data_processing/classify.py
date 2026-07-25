"""
classify_transactions.py

Reads uncategorised transactions out of transactions.db (created by
build_db.py) one calendar day at a time, sends each day's batch to a local
Gemma 3 12B model running under Ollama, and writes the results back to the
same row.

Categories come from the shared `Category` enum in models.py — the same
canonical set build_db.py uses for Monzo/Amex — so there's exactly one
definition of what a valid category is anywhere in the project. In practice
this script mostly only has Nationwide rows to do, since Monzo/Amex already
get categorised directly in build_db.py.

Setup:
    ollama pull gemma3:12b
    ollama serve                      # if not already running as a service
    pip install ollama sqlalchemy

    # optional, only needed if Ollama isn't on the default host/port:
    export OLLAMA_API_BASE="http://localhost:11434"

Usage:
    python classify_transactions.py
"""

import json
import os
import time
from collections import defaultdict

import ollama
from models.tables import Category
from sqlalchemy import MetaData, Table, create_engine, select, update

MODEL = "gemma3:12b"  # local model served by Ollama
API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
client = ollama.Client(host=API_BASE)

CATEGORIES = [c.value for c in Category]

SYSTEM_PROMPT = f"""You are a personal-finance transaction classifier.

Classify each transaction below into exactly one of these categories:
{", ".join(CATEGORIES)}

Rules / what each category means:
- "Groceries": supermarkets.
- "Eating out": restaurants and takeaways.
- "Shopping": general retail — clothes, electronics, department stores, online purchases.
- "Entertainment": cinema, streaming, events, hobbies, music/video.
- "Transport": daily commuting — buses, trains, tube, fuel, parking, taxis/rideshare for ordinary travel.
- "Holidays": trips away — flights, hotels, foreign transactions while travelling. Not day-to-day commuting.
- "Bills": recurring essential household bills — utilities, council tax, insurance, rent/mortgage.
- "Monthly Payments": other recurring monthly payments that aren't core household bills (e.g. subscriptions).
- "Personal care": health, pharmacy, grooming, medical.
- "Expenses": work/business expenses likely to be reimbursed.
- "Finances": fees, interest, savings, investments, financial admin.
- "Transfers": money moved between the person's own accounts (e.g. Monzo-to-Monzo, savings pots) — not a purchase.
- "Money Owed": repaying or receiving money between friends/family for shared costs — not a business transfer.
- "Income": salary, refunds, and other money coming in that isn't a transfer between own accounts.
- "Gifts": presents bought for other people.
- "Arsenal": spending specifically related to Arsenal FC (tickets, merchandise, subscriptions).
- "Golf": golf-related spending (green fees, equipment, club membership).
- "General": everyday miscellaneous spend that doesn't clearly fit any category above.

If genuinely unclear, use "General".

You will be given a numbered list of transactions for a single day. Respond ONLY with a JSON object
of the form {{"categories": ["Category1", "Category2", ...]}} with exactly one category per transaction,
in the same order they were given. Do not include any other text, explanation, or markdown formatting.
"""


def classify_day(day, rows, model=MODEL, max_retries=3):
    """Send one day's transactions to the LLM, return a list of categories in row order."""
    row_dicts = [dict(row._mapping) for row in rows]

    user_prompt = (
        f"Date: {day}\n\nTransactions:\n"
        + "\n\nRows:\n"
        + json.dumps(row_dicts, indent=2, default=str)
    )
    for attempt in range(max_retries):
        try:
            response = client.chat(
                model=model,
                messages=[
                    {"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_prompt},
                ],
                format="json",
                options={"temperature": 0},
            )
            content = response.message.content
            parsed = json.loads(content)
            categories = parsed["categories"]

            if len(categories) != len(rows):
                raise ValueError(
                    f"Expected {len(rows)} categories, got {len(categories)}"
                )

            # Normalise / validate against the known category list
            cleaned = []
            for cat in categories:
                cat = cat.strip()
                cleaned.append(cat if cat in CATEGORIES else Category.GENERAL.value)
            return cleaned

        except Exception as e:
            print(f"  [{day}] attempt {attempt + 1} failed: {e}")
            time.sleep(1.5 * (attempt + 1))

    print(f"  [{day}] giving up after {max_retries} attempts — leaving uncategorised")

    """Amex tags daily TfL commuter charges as 'Travel' in its own category field;
    treat these as ordinary commuting instead."""
    result = list([None] * len(rows))
    for i, row in enumerate(rows):
        if row.source == "amex" and "TFL" in (row.description or "").upper():
            result[i] = Category.TRANSPORT.value
    return result


def main():

    engine = create_engine("sqlite:///src/data/transactions.db")

    metadata = MetaData()
    transactions = Table("transactions", metadata, autoload_with=engine)
    state = Table("state", metadata, autoload_with=engine)

    with engine.connect() as conn:
        cutoff_date = conn.scalar(select(state.c.date_classified_upto))
        query = select(transactions)
        if cutoff_date is not None:
            query = query.where(transactions.c.date > cutoff_date)
        query = query.where(transactions.c.category.is_(None))
        query = query.order_by(transactions.c.date)
        all_rows = conn.execute(query).all()

    if not all_rows:
        print("Nothing to classify — every transaction already has a category.")
        return

    by_day = defaultdict(list)
    for row in all_rows:
        by_day[row.date].append(row)

    days = sorted(by_day.keys())

    print(f"{len(all_rows)} transactions across {len(days)} day(s) to classify.")

    total_classified = 0
    with engine.connect() as conn:
        for day in days:
            day_rows = by_day[day]
            print(f"Classifying {day} ({len(day_rows)} transactions)...")

            categories = classify_day(day, day_rows, model=MODEL)

            for row, category in zip(day_rows, categories):
                if category is None:
                    continue
                conn.execute(
                    update(transactions)
                    .where(transactions.c.id == row.id)
                    .values(category=Category(category))
                )
                total_classified += 1
                conn.execute(update(state).values(date_classified_upto=day))
                conn.commit()

    print(f"Done. Classified {total_classified}/{len(all_rows)} transactions.")


if __name__ == "__main__":
    main()
