# src/generate_fact_sales.py
import math
import random
import sqlite3

DB_PATH = "data/pricing.db"

# Baseline conversion by segment (before price effects)
SEGMENT_BASE_CVR = {
    "new": 0.020,
    "returning": 0.030,
    "price_sensitive": 0.018,
    "high_value": 0.040,
}

# Category price elasticity strength (higher -> more sensitive)
CATEGORY_ELASTICITY = {
    "electronics": 1.4,
    "home": 1.1,
    "beauty": 0.9,
    "sports": 1.0,
    "toys": 1.2,
}

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def fetch_joined_rows(conn):
    """
    Join the needed tables at sku_id x segment_id x date grain.
    We also join inventory at sku_id x date.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.sku_id,
            t.segment_id,
            t.date,
            t.sessions,
            t.add_to_cart,
            p.price_shown,
            p.promo_active,
            p.competitor_price,
            s.unit_cost,
            s.msrp,
            s.category,
            i.stockout_flag
        FROM fact_traffic t
        JOIN fact_prices_shown p
          ON t.sku_id = p.sku_id AND t.segment_id = p.segment_id AND t.date = p.date
        JOIN dim_sku s
          ON t.sku_id = s.sku_id
        JOIN fact_inventory i
          ON t.sku_id = i.sku_id AND t.date = i.date
        ORDER BY t.date, t.sku_id, t.segment_id
    """)
    return cur.fetchall()

def main(seed: int = 7):
    rng = random.Random(seed)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        rows_in = fetch_joined_rows(conn)

        out_rows = []

        for (
            sku_id, segment_id, d,
            sessions, add_to_cart,
            price, promo_active, competitor_price,
            unit_cost, msrp, category,
            stockout_flag
        ) in rows_in:
            sessions = int(sessions)
            add_to_cart = int(add_to_cart)
            price = float(price)
            unit_cost = float(unit_cost)
            msrp = float(msrp) if msrp is not None else price

            if stockout_flag == 1 or sessions == 0:
                orders = 0
                units_sold = 0
            else:
                base_cvr = SEGMENT_BASE_CVR.get(segment_id, 0.02)
                elasticity = CATEGORY_ELASTICITY.get(category, 1.0)

                # price position signals
                price_vs_msrp = price / msrp if msrp > 0 else 1.0
                price_vs_comp = price / float(competitor_price) if competitor_price else 1.0

                # convert to log space for smooth effects
                # higher price vs msrp reduces conversion; promo increases
                price_effect = -elasticity * math.log(price_vs_msrp + 1e-9)
                comp_effect = -0.6 * math.log(price_vs_comp + 1e-9)

                promo_effect = 0.35 if int(promo_active) == 1 else 0.0

                # add-to-cart provides extra intent signal
                intent = 0.15 * math.log(1 + add_to_cart)

                # Build a probability around base_cvr but bounded
                # We map (logit(base) + effects) -> sigmoid
                base_logit = math.log(base_cvr / (1 - base_cvr))
                logit = base_logit + price_effect + comp_effect + promo_effect + intent

                cvr = sigmoid(logit)
                cvr = clamp(cvr, 0.0001, 0.25)

                # Orders ~ Binomial(sessions, cvr) approximated by sum of Bernoulli (fast enough for this size)
                orders = 0
                # For speed, approximate with normal/poisson when sessions large
                if sessions <= 80:
                    for _ in range(sessions):
                        orders += 1 if rng.random() < cvr else 0
                else:
                    # poisson approximation
                    lam = sessions * cvr
                    # simple Poisson sampler (Knuth)
                    L = math.exp(-lam)
                    k = 0
                    p_acc = 1.0
                    while p_acc > L:
                        k += 1
                        p_acc *= rng.random()
                    orders = max(0, k - 1)

                # Units per order (UPO): beauty higher multi-unit, electronics mostly 1
                if category == "beauty":
                    upo = 1.0 + rng.random() * 0.8
                elif category == "home":
                    upo = 1.0 + rng.random() * 0.5
                else:
                    upo = 1.0 + rng.random() * 0.25

                units_sold = int(round(orders * upo))

            revenue = round(price * units_sold, 2)
            profit = round((price - unit_cost) * units_sold, 2)

            out_rows.append((sku_id, segment_id, d, orders, units_sold, revenue, profit))

        conn.executemany(
            """
            INSERT OR REPLACE INTO fact_sales
            (sku_id, segment_id, date, orders, units_sold, revenue, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            out_rows
        )
        conn.commit()
        print(f"✅ Inserted {len(out_rows)} rows into fact_sales")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
