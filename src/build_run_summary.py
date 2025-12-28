# src/build_run_summary.py
import sqlite3
from pathlib import Path

DB_PATH = "data/pricing.db"
SCHEMA_PATH = Path("sql/run_summary_schema.sql")

REASONS = [
    "MAX_DAILY_CHANGE_CLAMPED",
    "COMPETITOR_CAP_APPLIED",
    "MARGIN_FLOOR_APPLIED",
    "MAP_FLOOR_APPLIED",
]

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # creating summary table
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()

        run_date = cur.execute("SELECT MAX(run_date) FROM pricing_recommendations").fetchone()[0]
        if run_date is None:
            raise ValueError("No pricing_recommendations found")

        # base aggregates
        cur.execute("""
            SELECT
              COUNT(*) AS n,
              AVG(recommended_price) AS avg_price,
              SUM(expected_units) AS total_units,
              SUM(expected_profit) AS total_profit
            FROM pricing_recommendations
            WHERE run_date = ?
        """, (run_date,))
        n, avg_price, total_units, total_profit = cur.fetchone()

        # reason counts
        cur.execute("""
            SELECT reasons
            FROM pricing_recommendations
            WHERE run_date = ?
        """, (run_date,))

        counts = {r: 0 for r in REASONS}
        n_none = 0

        for (reasons,) in cur.fetchall():
            if reasons is None or reasons.strip() == "":
                n_none += 1
                continue
            parts = [p.strip() for p in reasons.split(",") if p.strip()]
            if not parts:
                n_none += 1
                continue
            for p in parts:
                if p in counts:
                    counts[p] += 1

        # rates
        def rate(x): 
            return float(x) / float(n) if n else 0.0

        row = (
            run_date,
            int(n),
            float(avg_price or 0.0),
            float(total_units or 0.0),
            float(total_profit or 0.0),

            int(n_none),
            int(counts["MAX_DAILY_CHANGE_CLAMPED"]),
            int(counts["COMPETITOR_CAP_APPLIED"]),
            int(counts["MARGIN_FLOOR_APPLIED"]),
            int(counts["MAP_FLOOR_APPLIED"]),

            rate(n_none),
            rate(counts["MAX_DAILY_CHANGE_CLAMPED"]),
            rate(counts["COMPETITOR_CAP_APPLIED"]),
            rate(counts["MARGIN_FLOOR_APPLIED"]),
            rate(counts["MAP_FLOOR_APPLIED"]),
        )

        cur.execute("""
            INSERT OR REPLACE INTO pricing_run_summary (
              run_date,
              n_recommendations,
              avg_recommended_price,
              total_expected_units,
              total_expected_profit,
              n_none, n_max_daily_change, n_competitor_cap, n_margin_floor, n_map_floor,
              r_none, r_max_daily_change, r_competitor_cap, r_margin_floor, r_map_floor
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
        conn.commit()

        print(f" Built pricing_run_summary for {run_date}")
        print(f"  n={n}, avg_price={avg_price:.2f}, total_exp_profit={total_profit:.2f}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
