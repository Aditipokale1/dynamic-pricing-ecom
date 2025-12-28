# src/validate_data.py
import sqlite3

DB_PATH = "data/pricing.db"

def scalar(conn, sql: str, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchone()[0]

def check_no_duplicates(conn):
    checks = [
        ("fact_traffic",
         "SELECT COUNT(*) - COUNT(DISTINCT sku_id || '|' || segment_id || '|' || date) FROM fact_traffic"),
        ("fact_prices_shown",
         "SELECT COUNT(*) - COUNT(DISTINCT sku_id || '|' || segment_id || '|' || date) FROM fact_prices_shown"),
        ("fact_sales",
         "SELECT COUNT(*) - COUNT(DISTINCT sku_id || '|' || segment_id || '|' || date) FROM fact_sales"),
        ("fact_inventory",
         "SELECT COUNT(*) - COUNT(DISTINCT sku_id || '|' || date) FROM fact_inventory"),
    ]
    for name, q in checks:
        dupes = scalar(conn, q)
        if dupes != 0:
            raise AssertionError(f"❌ {name}: found {dupes} duplicate-grain rows")
    print(" No duplicate-grain rows")

def check_ranges(conn):
    bad_price = scalar(conn, "SELECT COUNT(*) FROM fact_prices_shown WHERE price_shown <= 0")
    if bad_price != 0:
        raise AssertionError(f"❌ price_shown <= 0 rows: {bad_price}")

    bad_cost = scalar(conn, "SELECT COUNT(*) FROM dim_sku WHERE unit_cost <= 0")
    if bad_cost != 0:
        raise AssertionError(f"❌ unit_cost <= 0 rows: {bad_cost}")

    bad_prop = scalar(conn, """
        SELECT COUNT(*)
        FROM fact_prices_shown
        WHERE logging_propensity <= 0 OR logging_propensity > 1
    """)
    if bad_prop != 0:
        raise AssertionError(f"❌ bad logging_propensity rows: {bad_prop}")

    neg_sessions = scalar(conn, "SELECT COUNT(*) FROM fact_traffic WHERE sessions < 0 OR views < 0 OR add_to_cart < 0")
    if neg_sessions != 0:
        raise AssertionError(f"❌ negative traffic rows: {neg_sessions}")

    print(" Range checks passed")

def check_competitor_missing_rate(conn, threshold: float = 0.10):
    total = scalar(conn, "SELECT COUNT(*) FROM fact_prices_shown")
    missing = scalar(conn, "SELECT COUNT(*) FROM fact_prices_shown WHERE competitor_price IS NULL")
    rate = missing / total if total else 0.0
    if rate > threshold:
        raise AssertionError(f"❌ competitor_price missing rate {rate:.3%} > {threshold:.0%}")
    print(f" competitor_price missing rate: {rate:.3%}")

def check_abrupt_traffic_spikes(conn, spike_multiplier: float = 20.0):
    """
    Simple spike check:
    For each SKU+segment, compare MAX(sessions) to AVG(sessions).
    Flag if max > multiplier * avg (and avg > 0).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT sku_id, segment_id, MAX(sessions) AS mx, AVG(sessions) AS av
        FROM fact_traffic
        GROUP BY sku_id, segment_id
    """)
    flagged = 0
    for sku_id, seg, mx, av in cur.fetchall():
        if av is None or av <= 0:
            continue
        if mx > spike_multiplier * av:
            flagged += 1

    if flagged > 0:
        print(f"  Spike check: flagged {flagged} sku-segments with extreme session spikes")
    else:
        print(" Spike check passed (no extreme spikes)")


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        check_no_duplicates(conn)
        check_ranges(conn)
        check_competitor_missing_rate(conn, threshold=0.10)
        check_abrupt_traffic_spikes(conn, spike_multiplier=20.0)
        print(" All validation checks completed")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
