# src/validate_features.py
import sqlite3

DB_PATH = "data/pricing.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        total = cur.execute("SELECT COUNT(*) FROM feature_sku_segment_day").fetchone()[0]
        print(f"Total rows: {total}")

        # Rolling avg should always exist
        null_roll = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day
            WHERE price_rolling_avg_7d IS NULL
        """).fetchone()[0]
        print(f"price_rolling_avg_7d NULL: {null_roll}")

        # Price index may be null if competitor missing (should be near 0 in our data)
        null_pi = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day
            WHERE price_index_vs_comp IS NULL
        """).fetchone()[0]
        print(f"price_index_vs_comp NULL: {null_pi} ({null_pi/total:.2%})")

        # Lag null counts: expect roughly 1 per SKU×segment
        sku_seg = cur.execute("""
            SELECT COUNT(*) FROM (SELECT DISTINCT sku_id, segment_id FROM feature_sku_segment_day)
        """).fetchone()[0]

        null_sessions_lag = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day
            WHERE sessions_lag_1d IS NULL
        """).fetchone()[0]
        print(f"sessions_lag_1d NULL: {null_sessions_lag} (expected ~{sku_seg})")

        null_price_change = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day
            WHERE price_change_pct_1d IS NULL
        """).fetchone()[0]
        print(f"price_change_pct_1d NULL: {null_price_change} (expected ~{sku_seg})")

        # Flag rates
        low_stock = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day WHERE low_stock_flag=1
        """).fetchone()[0]
        overstock = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day WHERE overstock_flag=1
        """).fetchone()[0]
        print(f"low_stock_flag=1: {low_stock} ({low_stock/total:.2%})")
        print(f"overstock_flag=1: {overstock} ({overstock/total:.2%})")

        # Sanity: price > 0
        bad_price = cur.execute("""
            SELECT COUNT(*) FROM feature_sku_segment_day WHERE price_shown <= 0
        """).fetchone()[0]
        print(f"price_shown <= 0: {bad_price}")

        print("✅ Feature validation done")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
