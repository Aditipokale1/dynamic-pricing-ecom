# src/check_propensity.py
import sqlite3

DB_PATH = "data/pricing.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # Basic propensity stats
        cur.execute("""
            SELECT
              MIN(logging_propensity),
              AVG(logging_propensity),
              MAX(logging_propensity),
              SUM(CASE WHEN logging_propensity IS NULL THEN 1 ELSE 0 END) AS nulls,
              SUM(CASE WHEN logging_propensity <= 0 THEN 1 ELSE 0 END) AS nonpositive,
              SUM(CASE WHEN logging_propensity > 1 THEN 1 ELSE 0 END) AS gt1,
              COUNT(*) AS n
            FROM fact_prices_shown
        """)
        mn, av, mx, nulls, nonpos, gt1, n = cur.fetchone()

        print("Propensity summary:")
        print(f"  rows: {n}")
        print(f"  min:  {mn:.6f}")
        print(f"  avg:  {av:.6f}")
        print(f"  max:  {mx:.6f}")
        print(f"  nulls: {nulls}, <=0: {nonpos}, >1: {gt1}")

        # Approx bucket usage: comparing price_shown / msrp, rounded to nearest 0.05
        cur.execute("""
            SELECT
              ROUND((p.price_shown / s.msrp) * 20.0) / 20.0 AS approx_mult,
              COUNT(*) AS cnt
            FROM fact_prices_shown p
            JOIN dim_sku s ON p.sku_id = s.sku_id
            WHERE s.msrp IS NOT NULL AND s.msrp > 0
            GROUP BY approx_mult
            ORDER BY cnt DESC
            LIMIT 20
        """)
        print("\nApprox multiplier usage (top 20):")
        for mult, cnt in cur.fetchall():
            print(f"  {mult:.2f}: {cnt}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
