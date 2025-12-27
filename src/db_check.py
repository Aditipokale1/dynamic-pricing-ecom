# src/db_check.py
import sqlite3

DB_PATH = "data/pricing.db"

TABLES = [
    "dim_sku",
    "dim_segment",
    "dim_calendar",
    "fact_traffic",
    "fact_prices_shown",
    "fact_sales",
    "fact_inventory",
]

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        print("Table row counts:")
        for t in TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            n = cur.fetchone()[0]
            print(f"  {t}: {n}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
