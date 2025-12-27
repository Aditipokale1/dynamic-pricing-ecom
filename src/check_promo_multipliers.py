# src/check_promo_multipliers.py
import sqlite3

DB_PATH = "data/pricing.db"
ALLOWED = {0.90, 0.95, 1.00, 1.05, 1.10}

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # implied multiplier rounded to nearest 0.05
        cur.execute("""
            WITH x AS (
              SELECT
                p.promo_active AS promo_active,
                ROUND((p.price_shown / s.msrp) * 20.0) / 20.0 AS approx_mult
              FROM fact_prices_shown p
              JOIN dim_sku s ON p.sku_id = s.sku_id
              WHERE s.msrp IS NOT NULL AND s.msrp > 0
            )
            SELECT
              COUNT(*) AS total_rows,
              SUM(CASE WHEN promo_active=1 THEN 1 ELSE 0 END) AS promo_rows,
              SUM(CASE WHEN approx_mult NOT IN (0.90,0.95,1.00,1.05,1.10) THEN 1 ELSE 0 END) AS nonstandard_rows,
              SUM(CASE WHEN approx_mult NOT IN (0.90,0.95,1.00,1.05,1.10) AND promo_active=1 THEN 1 ELSE 0 END) AS nonstandard_promo_rows
            FROM x
        """)
        total, promo, nonstd, nonstd_promo = cur.fetchone()

        print("Promo vs non-standard implied multipliers:")
        print(f"  total rows: {total}")
        print(f"  promo rows: {promo} ({promo/total:.2%})")
        print(f"  non-standard multiplier rows: {nonstd} ({nonstd/total:.2%})")
        if nonstd > 0:
            print(f"  non-standard that are promo: {nonstd_promo} ({nonstd_promo/nonstd:.2%})")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
