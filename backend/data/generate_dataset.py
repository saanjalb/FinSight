"""
Synthetic transaction dataset generator for FinSight.

Produces 6 months of realistic personal-finance transactions with
deliberate patterns so every downstream demo feature has real data
to work with:

  - Monthly salary (income)                    -> analytics, forecasting
  - Fixed recurring bills (rent, utilities)     -> subscription detection
  - Recurring subscriptions (Netflix, Spotify)  -> subscription detection
  - A rent increase in the middle of the range  -> "amount changed" detection
  - A deliberate food-spending spike in one
    month (more orders + higher amounts)        -> spending-leak detection
  - Random everyday spending (food, shopping,
    transport, entertainment)                   -> general analytics

Run with: python backend/data/generate_dataset.py
Output:   backend/data/transactions.csv
"""
import csv
import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

random.seed(42)  # reproducible dataset across runs

OUTPUT_PATH = "backend/data/transactions.csv"

# 6 months, most recent month is the current one
NUM_MONTHS = 6
today = date.today()
START_MONTH = date(today.year, today.month, 1) - relativedelta(months=NUM_MONTHS - 1)

# The month index (0-based, last month) where we inject a food spending spike
SPIKE_MONTH_INDEX = NUM_MONTHS - 1  # most recent month
# The month index where rent increases
RENT_INCREASE_MONTH_INDEX = NUM_MONTHS - 2

rows = []
txn_id_counter = 1


def add_row(txn_date, merchant, amount, txn_type, category, description=""):
    global txn_id_counter
    rows.append({
        "date": txn_date.isoformat(),
        "merchant": merchant,
        "amount": round(amount, 2),
        "transaction_type": txn_type,
        "category": category,
        "description": description,
    })
    txn_id_counter += 1


for month_index in range(NUM_MONTHS):
    month_start = START_MONTH + relativedelta(months=month_index)

    # --- Income: salary on the 1st ---
    add_row(month_start, "SALARY", 52000, "income", "Income", "Monthly salary")

    # --- Fixed recurring bills ---
    rent_amount = 16000 if month_index >= RENT_INCREASE_MONTH_INDEX else 15000
    add_row(month_start + timedelta(days=2), "RENT PAYMENT", rent_amount, "expense", "Housing", "Monthly rent")
    add_row(month_start + timedelta(days=4), "ELECTRICITY BOARD", random.uniform(1000, 1400), "expense", "Utilities")
    add_row(month_start + timedelta(days=4), "INTERNET PROVIDER", 999, "expense", "Utilities", "Broadband")

    # --- Recurring subscriptions (same merchant, same amount, same day each month) ---
    add_row(month_start + timedelta(days=6), "NETFLIX", 649, "expense", "Subscriptions")
    add_row(month_start + timedelta(days=8), "SPOTIFY", 119, "expense", "Subscriptions")
    add_row(month_start + timedelta(days=10), "CLOUD STORAGE", 130, "expense", "Subscriptions")
    if month_index >= 2:  # gym membership starts a couple months in
        add_row(month_start + timedelta(days=5), "FITNESS GYM", 1500, "expense", "Subscriptions")

    # --- Food & dining: baseline, with a deliberate spike in the last month ---
    is_spike_month = month_index == SPIKE_MONTH_INDEX
    num_food_orders = random.randint(20, 24) if not is_spike_month else random.randint(30, 34)
    for _ in range(num_food_orders):
        day_offset = random.randint(0, 27)
        merchant = random.choice(["SWIGGY", "ZOMATO", "DOMINOS", "LOCAL CAFE"])
        base_amount = random.uniform(200, 450)
        amount = base_amount * 1.3 if is_spike_month else base_amount  # spike month also costs more per order
        add_row(month_start + timedelta(days=day_offset), merchant, amount, "expense", "Food & Dining", "Food delivery")

    # --- Transport ---
    for _ in range(random.randint(10, 16)):
        day_offset = random.randint(0, 27)
        merchant = random.choice(["UBER", "OLA", "METRO CARD RECHARGE"])
        add_row(month_start + timedelta(days=day_offset), merchant, random.uniform(80, 350), "expense", "Transport")

    # --- Shopping (irregular) ---
    for _ in range(random.randint(2, 5)):
        day_offset = random.randint(0, 27)
        merchant = random.choice(["AMAZON", "MYNTRA", "FLIPKART"])
        add_row(month_start + timedelta(days=day_offset), merchant, random.uniform(500, 3500), "expense", "Shopping")

    # --- Entertainment (irregular) ---
    for _ in range(random.randint(1, 3)):
        day_offset = random.randint(0, 27)
        merchant = random.choice(["BOOKMYSHOW", "PVR CINEMAS"])
        add_row(month_start + timedelta(days=day_offset), merchant, random.uniform(300, 900), "expense", "Entertainment")

    # --- Healthcare (occasional) ---
    if random.random() < 0.4:
        day_offset = random.randint(0, 27)
        add_row(month_start + timedelta(days=day_offset), "APOLLO PHARMACY", random.uniform(200, 1200), "expense", "Healthcare")

# Sort chronologically
rows.sort(key=lambda r: r["date"])

import os
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "merchant", "amount", "transaction_type", "category", "description"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} transactions across {NUM_MONTHS} months -> {OUTPUT_PATH}")
print(f"Date range: {rows[0]['date']} to {rows[-1]['date']}")
print(f"Spike month index: {SPIKE_MONTH_INDEX} (0-based, most recent)")
print(f"Rent increase from month index: {RENT_INCREASE_MONTH_INDEX}")
