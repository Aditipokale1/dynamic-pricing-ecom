# src/generate_fact_traffic.py
import math
import random
import sqlite3
from collections import defaultdict

DB_PATH = "data/pricing.db"

SEGMENT_MULT = {
    "new": 1.00,
    "returning": 0.70,
    "price_sensitive": 1.20,
    "high_value": 0.45,
}

CATEGORY_BASE_SESSIONS = {
    "electronics": (8, 60),
    "home": (6, 45),
    "beauty": (10, 80),
    "sports": (6, 50),
    "toys": (7, 65),
}

def fetch_skus(conn):
    cur = conn.cursor()
    cur.execute("SELECT sku_id, category, is_kvi FROM dim_sku")
    return cur.fetchall()

def fetch_calendar(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT date, day_of_week, is_holiday, month
        FROM dim_calendar
        ORDER BY date
    """)
    return cur.fetchall()

def fetch_segments(conn):
    cur = conn.cursor()
    cur.execute("SELECT segment_id FROM dim_segment")
    return [r[0] for r in cur.fetchall()]

def clamp_int(x: float) -> int:
    return max(0, int(round(x)))

def main(seed: int = 999):
    rng = random.Random(seed)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        skus = fetch_skus(conn)
        cal = fetch_calendar(conn)
        segments = fetch_segments(conn)

        rows = []

        # give each sku a baseline popularity weight
        sku_pop = {}
        for sku_id, category, is_kvi in skus:
            # KVI items tend to have higher traffic
            base = rng.uniform(0.6, 1.4) * (1.25 if is_kvi == 1 else 1.0)
            sku_pop[sku_id] = base

        for (d, dow, is_holiday, month) in cal:
            # weekly seasonality: weekends higher browsing
            weekend_boost = 1.25 if dow in (5, 6) else 1.0
            holiday_boost = 1.50 if is_holiday == 1 else 1.0

            # mild monthly seasonality (example)
            month_boost = 1.10 if month in (11, 12) else 1.0

            day_mult = weekend_boost * holiday_boost * month_boost

            for sku_id, category, is_kvi in skus:
                base_lo, base_hi = CATEGORY_BASE_SESSIONS[category]
                base_sessions = rng.uniform(base_lo, base_hi) * sku_pop[sku_id] * day_mult

                for seg in segments:
                    seg_mult = SEGMENT_MULT.get(seg, 1.0)

                    sessions = base_sessions * seg_mult * rng.uniform(0.85, 1.15)

                    # views roughly proportional; add-to-cart fraction varies
                    views = sessions * rng.uniform(1.8, 4.5)

                    # add-to-cart: lower on high_value (they may buy quickly later), higher on price_sensitive browsing
                    if seg == "price_sensitive":
                        atc_rate = rng.uniform(0.05, 0.12)
                    elif seg == "high_value":
                        atc_rate = rng.uniform(0.02, 0.07)
                    else:
                        atc_rate = rng.uniform(0.03, 0.09)

                    add_to_cart = sessions * atc_rate

                    rows.append((
                        sku_id, seg, d,
                        clamp_int(sessions),
                        clamp_int(views),
                        clamp_int(add_to_cart),
                    ))

        conn.executemany(
            """
            INSERT OR REPLACE INTO fact_traffic
            (sku_id, segment_id, date, sessions, views, add_to_cart)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        print(f"✅ Inserted {len(rows)} rows into fact_traffic")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
