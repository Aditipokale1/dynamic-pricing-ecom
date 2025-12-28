# src/generate_fact_inventory.py
import random
import sqlite3
from collections import defaultdict

DB_PATH = "data/pricing.db"

def fetch_skus(conn):
    cur = conn.cursor()
    cur.execute("SELECT sku_id, category FROM dim_sku")
    return cur.fetchall()

def fetch_dates(conn):
    cur = conn.cursor()
    cur.execute("SELECT date FROM dim_calendar ORDER BY date")
    return [r[0] for r in cur.fetchall()]

def base_daily_demand(category: str, rng: random.Random) -> float:
    # rough category-level demand intensity
    if category == "electronics":
        return rng.uniform(0.4, 2.0)
    if category == "home":
        return rng.uniform(0.6, 3.0)
    if category == "beauty":
        return rng.uniform(1.0, 6.0)
    if category == "sports":
        return rng.uniform(0.6, 3.5)
    return rng.uniform(0.8, 4.0)  # toys

def main(seed: int = 123):
    rng = random.Random(seed)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        skus = fetch_skus(conn)
        dates = fetch_dates(conn)

        rows = []
        # tracking recent sales proxy for DOC estimate
        rolling_sales = defaultdict(list)  # sku_id -> list of last 7 "demand" draws

        for sku_id, category in skus:
            # starting inventory depends on category
            if category == "electronics":
                on_hand = rng.randint(10, 80)
            elif category == "beauty":
                on_hand = rng.randint(80, 400)
            else:
                on_hand = rng.randint(30, 200)

            # restocking cadence: every 7-21 days
            restock_every = rng.randint(7, 21)
            next_restock_idx = rng.randint(0, restock_every - 1)

            demand_mu = base_daily_demand(category, rng)

            for day_idx, d in enumerate(dates):
                inbound = 0

                # restock event
                if day_idx == next_restock_idx:
                    # restock size scales with category
                    if category == "electronics":
                        inbound = rng.randint(10, 60)
                    elif category == "beauty":
                        inbound = rng.randint(50, 250)
                    else:
                        inbound = rng.randint(20, 120)

                    on_hand += inbound
                    next_restock_idx += restock_every
                    restock_every = rng.randint(7, 21)  # vary cadence

                demand = 0
                trials = int(demand_mu * 6) + 1
                p = min(0.7, demand_mu / max(1, trials))
                for _ in range(trials):
                    demand += 1 if rng.random() < p else 0

                # fulfilling demand from on_hand
                fulfilled = min(on_hand, demand)
                on_hand -= fulfilled

                stockout_flag = 1 if on_hand == 0 else 0

                # days of cover estimate: on_hand / avg(last7 fulfilled + small epsilon)
                rolling_sales[sku_id].append(fulfilled)
                last7 = rolling_sales[sku_id][-7:]
                avg7 = sum(last7) / max(1, len(last7))
                days_of_cover = None
                if avg7 > 0:
                    days_of_cover = round(on_hand / avg7, 2)

                rows.append((sku_id, d, int(on_hand), int(inbound), int(stockout_flag), days_of_cover))

        conn.executemany(
            """
            INSERT OR REPLACE INTO fact_inventory
            (sku_id, date, on_hand, inbound, stockout_flag, days_of_cover)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        print(f"✅ Inserted {len(rows)} rows into fact_inventory")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
