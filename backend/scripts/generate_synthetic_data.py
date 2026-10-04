"""
Synthetic transaction data generator for FinSight.

This produces a 6-month CSV of realistic personal transactions, with
specific patterns deliberately built in so later features have something
real to detect:

- Monthly salary (income)
- Recurring subscriptions at fixed amounts (Netflix, Spotify, gym, cloud
  storage, internet) — for the subscription/leak detector in Phase 5
- A clear food-spending increase in the most recent month — for the
  spending-leak / anomaly detection demo
- Enough transaction volume and history for forecasting to be meaningful
- Varied one-off merchants across categories for realistic analytics

Run with: python3 backend/scripts/generate_synthetic_data.py
Output:   backend/data/synthetic_transactions.csv
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)  # reproducible dataset

OUTPUT_PATH = "backend/data/synthetic_transactions.csv"

# 6 months, most recent month last (index 5 = current/most recent month)
MONTHS = [
    date(2026, 4, 1),
    date(2026, 5, 1),
    date(2026, 6, 1),
    date(2026, 7, 1),
    date(2026, 8, 1),
    date(2026, 9, 1),
]

RECURRING = [
    ("Netflix", 649, "Subscriptions"),
    ("Spotify", 119, "Subscriptions"),
    ("Airtel Broadband", 999, "Utilities"),
    ("Cult Fit Gym", 1500, "Healthcare"),
    ("Google One Storage", 130, "Subscriptions"),
]

FOOD_MERCHANTS = ["Swiggy", "Zomato", "Domino's", "Starbucks", "Local Cafe"]
SHOPPING_MERCHANTS = ["Amazon", "Myntra", "Flipkart", "H&M", "Decathlon"]
TRANSPORT_MERCHANTS = ["Uber", "Ola", "Rapido", "IndianOil Petrol"]
OTHER_EXPENSE_MERCHANTS = [
    ("BookMyShow", "Entertainment"),
    ("Apollo Pharmacy", "Healthcare"),
    ("Coursera", "Education"),
    ("Electricity Board", "Utilities"),
]


def month_range(month_start: date):
    """All days in a given month."""
    next_month = date(
        month_start.year + (1 if month_start.month == 12 else 0),
        1 if month_start.month == 12 else month_start.month + 1,
        1,
    )
    days = (next_month - month_start).days
    return [month_start + timedelta(days=i) for i in range(days)]


def generate_transactions():
    rows = []
    tx_id = 1

    for month_index, month_start in enumerate(MONTHS):
        days_in_month = month_range(month_start)
        is_latest_month = month_index == len(MONTHS) - 1

        # --- Income: salary on the 1st ---
        rows.append({
            "id": tx_id, "date": month_start.isoformat(), "merchant": "Salary",
            "amount": 75000, "transaction_type": "income",
            "category": "Income", "description": "Monthly salary credit",
        })
        tx_id += 1

        # --- Recurring subscriptions, same day each month, same amount ---
        for merchant, amount, category in RECURRING:
            rows.append({
                "id": tx_id, "date": (month_start + timedelta(days=4)).isoformat(),
                "merchant": merchant, "amount": amount, "transaction_type": "expense",
                "category": category, "description": f"Monthly {merchant} charge",
            })
            tx_id += 1

        # --- Rent, fixed, on the 3rd ---
        rows.append({
            "id": tx_id, "date": (month_start + timedelta(days=2)).isoformat(),
            "merchant": "Rent Payment", "amount": 15000, "transaction_type": "expense",
            "category": "Housing", "description": "Monthly rent",
        })
        tx_id += 1

        # --- Food delivery: deliberately spikes in the latest month ---
        food_tx_count = 27 if is_latest_month else random.randint(10, 16)
        for _ in range(food_tx_count):
            day = random.choice(days_in_month)
            merchant = random.choice(FOOD_MERCHANTS)
            amount = round(random.uniform(180, 550), 2)
            rows.append({
                "id": tx_id, "date": day.isoformat(), "merchant": merchant,
                "amount": amount, "transaction_type": "expense",
                "category": "Food & Dining", "description": "Food delivery/dining",
            })
            tx_id += 1

        # --- Shopping: normal random volume ---
        for _ in range(random.randint(4, 8)):
            day = random.choice(days_in_month)
            merchant = random.choice(SHOPPING_MERCHANTS)
            amount = round(random.uniform(500, 4000), 2)
            rows.append({
                "id": tx_id, "date": day.isoformat(), "merchant": merchant,
                "amount": amount, "transaction_type": "expense",
                "category": "Shopping", "description": "Online purchase",
            })
            tx_id += 1

        # --- Transport: frequent small charges ---
        for _ in range(random.randint(8, 14)):
            day = random.choice(days_in_month)
            merchant = random.choice(TRANSPORT_MERCHANTS)
            amount = round(random.uniform(80, 400), 2)
            rows.append({
                "id": tx_id, "date": day.isoformat(), "merchant": merchant,
                "amount": amount, "transaction_type": "expense",
                "category": "Transport", "description": "Ride/fuel",
            })
            tx_id += 1

        # --- A handful of miscellaneous category expenses ---
        for _ in range(random.randint(2, 4)):
            day = random.choice(days_in_month)
            merchant, category = random.choice(OTHER_EXPENSE_MERCHANTS)
            amount = round(random.uniform(200, 2500), 2)
            rows.append({
                "id": tx_id, "date": day.isoformat(), "merchant": merchant,
                "amount": amount, "transaction_type": "expense",
                "category": category, "description": "Miscellaneous expense",
            })
            tx_id += 1

    rows.sort(key=lambda r: r["date"])
    return rows


def write_csv(rows):
    import os
    os.makedirs("backend/data", exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "date", "merchant", "amount", "transaction_type",
            "category", "description",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} transactions to {OUTPUT_PATH}")


if __name__ == "__main__":
    write_csv(generate_transactions())
