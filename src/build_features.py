# src/build_features.py
import sqlite3
from pathlib import Path
import yaml

DB_PATH = "data/pricing.db"
FEATURE_SCHEMA_PATH = Path("sql/features_schema.sql")
POLICY_PATH = Path("src/config/pricing_policy.yaml")

def load_policy():
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    policy = load_policy()
    low_lt = float(policy["inventory_flags"]["low_stock_days_of_cover_lt"])
    over_gt = float(policy["inventory_flags"]["overstock_days_of_cover_gt"])

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # Creating feature table
        schema_sql = FEATURE_SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()

        # Pulling base joined rows ordered for lag/rolling calcs
        cur.execute("""
            SELECT
              t.sku_id, t.segment_id, t.date,
              t.sessions, t.views, t.add_to_cart,
              p.price_shown, p.discount_pct_vs_msrp, p.competitor_price,
              i.on_hand, i.inbound, i.stockout_flag, i.days_of_cover,
              s.orders, s.units_sold, s.revenue, s.profit
            FROM fact_traffic t
            JOIN fact_prices_shown p
              ON t.sku_id=p.sku_id AND t.segment_id=p.segment_id AND t.date=p.date
            JOIN fact_sales s
              ON t.sku_id=s.sku_id AND t.segment_id=s.segment_id AND t.date=s.date
            JOIN fact_inventory i
              ON t.sku_id=i.sku_id AND t.date=i.date
            ORDER BY t.sku_id, t.segment_id, t.date
        """)
        rows = cur.fetchall()

        # Building features with lags/rolling windows per SKU×segment
        out = []
        last_price = None
        last_sessions = None
        rolling_prices = []  # last up to 7 prices
        last_key = None

        def reset_state():
            nonlocal last_price, last_sessions, rolling_prices
            last_price = None
            last_sessions = None
            rolling_prices = []

        for r in rows:
            (
                sku_id, segment_id, d,
                sessions, views, add_to_cart,
                price_shown, discount_pct_vs_msrp, competitor_price,
                on_hand, inbound, stockout_flag, days_of_cover,
                orders, units_sold, revenue, profit
            ) = r

            key = (sku_id, segment_id)
            if key != last_key:
                reset_state()
                last_key = key

            price_shown = float(price_shown)
            comp = float(competitor_price) if competitor_price is not None else None

            price_index_vs_comp = (price_shown / comp) if (comp and comp > 0) else None

            # lag features
            sessions_lag_1d = int(last_sessions) if last_sessions is not None else None

            price_change_pct_1d = None
            if last_price is not None and last_price > 0:
                price_change_pct_1d = (price_shown - last_price) / last_price

            # rolling avg price (7d)
            rolling_prices.append(price_shown)
            if len(rolling_prices) > 7:
                rolling_prices.pop(0)
            price_rolling_avg_7d = sum(rolling_prices) / len(rolling_prices)

            # inventory flags
            doc = float(days_of_cover) if days_of_cover is not None else None
            low_stock_flag = 1 if (doc is not None and doc < low_lt) else 0
            overstock_flag = 1 if (doc is not None and doc > over_gt) else 0

            out.append((
                sku_id, segment_id, d,
                price_shown,
                float(discount_pct_vs_msrp) if discount_pct_vs_msrp is not None else None,
                float(price_index_vs_comp) if price_index_vs_comp is not None else None,
                float(price_change_pct_1d) if price_change_pct_1d is not None else None,
                float(price_rolling_avg_7d),

                int(sessions), int(views), int(add_to_cart),
                sessions_lag_1d,

                int(on_hand), int(inbound), int(stockout_flag),
                doc,
                int(low_stock_flag), int(overstock_flag),

                int(orders), int(units_sold),
                float(revenue), float(profit)
            ))

            last_price = price_shown
            last_sessions = sessions

        # Writing to DB 
        conn.execute("DELETE FROM feature_sku_segment_day;")
        conn.executemany(
            """
            INSERT INTO feature_sku_segment_day (
              sku_id, segment_id, date,
              price_shown, discount_pct_vs_msrp, price_index_vs_comp,
              price_change_pct_1d, price_rolling_avg_7d,
              sessions, views, add_to_cart, sessions_lag_1d,
              on_hand, inbound, stockout_flag, days_of_cover,
              low_stock_flag, overstock_flag,
              orders, units_sold, revenue, profit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            out
        )
        conn.commit()
        print(f" Built feature_sku_segment_day with {len(out)} rows")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
