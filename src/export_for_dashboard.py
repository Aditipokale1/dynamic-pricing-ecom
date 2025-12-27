# src/export_for_dashboard.py
import sqlite3
import csv
from pathlib import Path

DB_PATH = "data/pricing.db"
OUT_DIR = Path("dashboards/exports")

def export_query(conn, query: str, params, out_path: Path):
    cur = conn.cursor()
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    print(f"✅ Wrote {out_path} ({len(rows)} rows)")

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        run_date = cur.execute("SELECT MAX(run_date) FROM pricing_recommendations").fetchone()[0]
        if run_date is None:
            raise ValueError("No pricing_recommendations found")

        export_query(
            conn,
            "SELECT * FROM pricing_run_summary ORDER BY run_date",
            (),
            OUT_DIR / "pricing_run_summary.csv",
        )

        export_query(
            conn,
            """
            SELECT *
            FROM pricing_recommendations
            WHERE run_date = ?
            ORDER BY expected_profit DESC
            """,
            (run_date,),
            OUT_DIR / f"pricing_recommendations_{run_date}.csv",
        )

    finally:
        conn.close()

if __name__ == "__main__":
    main()
