# src/generate_fact_prices_shown.py
import random
import sqlite3

DB_PATH = "data/pricing.db"

# Logging policy: discrete multipliers (like buckets)
MULTIPLIERS = [0.90, 0.95, 1.00, 1.05, 1.10]

SEGMENT_PRICE_PREF = {
    "new": 0.0,
    "returning": 0.03,
    "price_sensitive": -0.05,  # more likely to see lower prices
    "high_value": 0.06,        # more likely to see higher prices
}

def fetch_skus(conn):
    cur = conn.cursor()
    cur.execute("SELECT sku_id, unit_cost, msrp, is_kvi FROM dim_sku")
    return cur.fetchall()

def fetch_segments(conn):
    cur = conn.cursor()
    cur.execute("SELECT segment_id FROM dim_segment")
    return [r[0] for r in cur.fetchall()]

def fetch_dates(conn):
    cur = conn.cursor()
    cur.execute("SELECT date, is_holiday, month FROM dim_calendar ORDER BY date")
    return cur.fetchall()

def round_price(p: float) -> float:
    # keep it simple for now (we'll do .99 endings later)
    return round(p, 2)

def softmax(scores):
    import math
    mx = max(scores)
    exps = [math.exp(s - mx) for s in scores]
    s = sum(exps)
    return [e / s for e in exps]

def main(seed: int = 2025):
    rng = random.Random(seed)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        skus = fetch_skus(conn)
        segments = fetch_segments(conn)
        dates = fetch_dates(conn)

        rows = []

        for (d, is_holiday, month) in dates:
            # promos more likely in Nov/Dec + holidays
            promo_day = (month in (11, 12) and rng.random() < 0.08) or (is_holiday == 1 and rng.random() < 0.20)

            for (sku_id, unit_cost, msrp, is_kvi) in skus:
                unit_cost = float(unit_cost)
                msrp = float(msrp) if msrp is not None else unit_cost * 2.0

                # Competitor price: noisy around "market" (between cost*1.2 and msrp*1.05)
                market = rng.uniform(unit_cost * 1.25, msrp * 1.02)
                competitor_price = market * rng.uniform(0.96, 1.04)

                # Promo price if promo_day triggers (not all SKUs participate)
                promo_active = 1 if (promo_day and rng.random() < 0.18) else 0
                promo_price = None
                if promo_active == 1:
                    # promo discount 10% to 35% off msrp, but never below cost*1.05
                    promo_price = max(unit_cost * 1.05, msrp * rng.uniform(0.65, 0.90))

                for seg in segments:
                    # create multiplier probabilities influenced by segment + KVI (KVI slightly lower prices)
                    seg_bias = SEGMENT_PRICE_PREF.get(seg, 0.0)
                    kvi_bias = -0.02 if is_kvi == 1 else 0.0

                    # score each multiplier
                    # lower multiplier is favored when seg_bias is negative
                    scores = []
                    for m in MULTIPLIERS:
                        # center around 1.0; negative bias pulls toward lower multipliers
                        score = -abs(m - (1.0 + seg_bias + kvi_bias)) * 8.0
                        scores.append(score)

                    probs = softmax(scores)

                    # sample multiplier
                    choice_idx = 0
                    r = rng.random()
                    cum = 0.0
                    for i, p in enumerate(probs):
                        cum += p
                        if r <= cum:
                            choice_idx = i
                            break

                    chosen_m = MULTIPLIERS[choice_idx]
                    propensity = probs[choice_idx]

                    # base price from msrp * multiplier, but keep above cost*1.05
                    price = max(unit_cost * 1.05, msrp * chosen_m)

                    # if promo active, price_shown becomes promo price (still log propensity as if policy chose it)
                    if promo_active == 1 and promo_price is not None:
                        price = promo_price

                    price = round_price(price)

                    discount_pct_vs_msrp = None
                    if msrp > 0:
                        discount_pct_vs_msrp = round(1.0 - (price / msrp), 4)

                    rows.append((
                        sku_id, seg, d,
                        price,
                        promo_active,
                        discount_pct_vs_msrp,
                        round_price(competitor_price),
                        round(propensity, 6),
                    ))

        conn.executemany(
            """
            INSERT OR REPLACE INTO fact_prices_shown
            (sku_id, segment_id, date, price_shown, promo_active, discount_pct_vs_msrp, competitor_price, logging_propensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        print(f"✅ Inserted {len(rows)} rows into fact_prices_shown")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
