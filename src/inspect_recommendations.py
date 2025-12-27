# src/inspect_recommendations.py
import sqlite3
from collections import Counter

DB_PATH = "data/pricing.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        run_date = cur.execute("SELECT MAX(run_date) FROM pricing_recommendations").fetchone()[0]
        if run_date is None:
            raise ValueError("No recommendations found")
        print(f"Run date: {run_date}\n")

        # Sample 10
        cur.execute("""
            SELECT sku_id, segment_id, recommended_price, expected_units, expected_profit, reasons
            FROM pricing_recommendations
            WHERE run_date = ?
            ORDER BY expected_profit DESC
            LIMIT 10
        """, (run_date,))
        print("Top 10 by expected_profit:")
        for sku, seg, price, eu, ep, reasons in cur.fetchall():
            print(f"  {sku} | {seg:14s} | price={price:8.2f} | exp_units={eu:7.4f} | exp_profit={ep:8.4f} | {reasons}")

        # Reason code hit rates
        cur.execute("""
            SELECT reasons
            FROM pricing_recommendations
            WHERE run_date = ?
        """, (run_date,))
        ctr = Counter()
        total = 0
        for (reasons,) in cur.fetchall():
            total += 1
            if reasons is None or reasons.strip() == "":
                ctr["(none)"] += 1
            else:
                for r in reasons.split(","):
                    r = r.strip()
                    if r:
                        ctr[r] += 1

        print("\nReason code counts:")
        for k, v in ctr.most_common():
            print(f"  {k}: {v} ({v/total:.2%})")

        # Compare recommended vs logged price (avg)
        cur.execute("""
            SELECT AVG(r.recommended_price), AVG(p.price_shown)
            FROM pricing_recommendations r
            JOIN fact_prices_shown p
              ON r.sku_id=p.sku_id AND r.segment_id=p.segment_id AND r.run_date=p.date
            WHERE r.run_date = ?
        """, (run_date,))
        avg_rec, avg_logged = cur.fetchone()
        print(f"\nAvg recommended price: {avg_rec:.2f}")
        print(f"Avg logged price:       {avg_logged:.2f}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
