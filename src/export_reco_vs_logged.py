import sqlite3
import csv
from pathlib import Path

DB_PATH = "data/pricing.db"
OUT = Path("dashboards/exports/reco_vs_logged.csv")

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        run_date = conn.execute("SELECT MAX(run_date) FROM pricing_recommendations").fetchone()[0]

        rows = conn.execute("""
            SELECT
              r.run_date,
              r.sku_id,
              r.segment_id,
              r.recommended_price,
              p.price_shown AS logged_price,
              (r.recommended_price - p.price_shown) AS delta_price,
              (r.recommended_price - p.price_shown) / p.price_shown AS delta_pct,
              r.expected_units,
              r.expected_profit,
              r.reasons
            FROM pricing_recommendations r
            JOIN fact_prices_shown p
              ON r.sku_id = p.sku_id
             AND r.segment_id = p.segment_id
             AND r.run_date = p.date
            WHERE r.run_date = ?
        """, (run_date,)).fetchall()

        cols = ["run_date","sku_id","segment_id","recommended_price","logged_price",
                "delta_price","delta_pct","expected_units","expected_profit","reasons"]

        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)

        print(f"✅ Wrote {OUT} ({len(rows)} rows)")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
