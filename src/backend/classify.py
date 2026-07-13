"""
classify_transactions.py

Reads uncategorised transactions out of transactions.db (created by
build_db.py) one calendar day at a time, sends each day's batch to
Gemma 4 31B (via LiteLLM / the Gemini API) for categorisation, and
writes the results back to the same row.

Setup:
    export GEMINI_API_KEY="your-key-here"
    pip install litellm sqlalchemy

Usage:
    python classify_transactions.py --db transactions.db
    python classify_transactions.py --db transactions.db --limit 5   # first 5 days only, for testing
    python classify_transactions.py --db transactions.db --recategorise  # ignore existing categories
"""

import json
import os
import time
from collections import defaultdict

import litellm
from sqlalchemy import MetaData, Table, create_engine, select, update

MODEL = "gemini/gemma-4-31b-it"  # served via the Gemini API; needs GEMINI_API_KEY

CATEGORIES = [
    "Groceries",
    "Eating Out",
    "Bars & Cafés",
    "Entertainment",
    "Shopping",
    "Transport",
    "Travel",
    "Bills & Utilities",
    "Health & Personal Care",
    "Professional Services",
    "Finances & Fees",
    "Transfers",
    "Income",
    "Gifts",
    "Sports & Hobbies",
    "Other",
]

SYSTEM_PROMPT = f"""You are a personal-finance transaction classifier.

Classify each transaction below into exactly one of these categories:
{", ".join(CATEGORIES)}

Rules:
- Use "Income" for salary, refunds, and money coming in.
- Use "Transfers" for money moved between the person's own accounts (e.g. Monzo-to-Monzo, savings pots), not purchases.
- Use "Transport" for daily commuting (TfL, buses, trains, fuel, parking, taxis/rideshare for ordinary travel).
- Use "Travel" only for holidays/trips (flights, hotels, foreign transactions while travelling).
- Use "Bars & Cafés" for coffee shops, pubs, and bars; use "Eating Out" for restaurants and takeaways.
- If genuinely unclear, use "Other".

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
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_prompt},
                ],
                temperature=0,
                api_key=os.getenv("GEMINI_API_KEY"),
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
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
                cleaned.append(cat if cat in CATEGORIES else "Other")
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
            result[i] = "Transport"
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

            categories = classify_day(day, day_rows, model="gemini/gemma-4-31b-it")

            for row, category in zip(day_rows, categories):
                if category is None:
                    continue
                conn.execute(
                    update(transactions)
                    .where(transactions.c.id == row.id)
                    .values(category=category)
                )
                total_classified += 1
        last_processed_date = day_rows[-1].date
        conn.execute(update(state).values(date_classified_upto=last_processed_date))
        conn.commit()

    print(f"Done. Classified {total_classified}/{len(all_rows)} transactions.")


if __name__ == "__main__":
    main()
