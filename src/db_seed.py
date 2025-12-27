# src/db_seed.py
import sqlite3
from datetime import date, timedelta

DB_PATH = "data/pricing.db"

SEGMENTS = [
    ("new", "First-time visitors / new customers"),
    ("returning", "Returning customers"),
    ("price_sensitive", "More likely to respond to discounts"),
    ("high_value", "Higher willingness to pay"),
]


def season_for_month(m: int) -> str:
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def seed_segments(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO dim_segment (segment_id, description)
        VALUES (?, ?)
        """,
        SEGMENTS,
    )


def seed_calendar(conn: sqlite3.Connection, start: date, end: date) -> None:
    # end is inclusive
    rows = []
    d = start
    while d <= end:
        dow = d.weekday()  # Mon=0..Sun=6
        week_of_year = int(d.strftime("%V"))
        month = d.month

        # simple starter flags (you can improve later)
        is_holiday = 1 if (d.month == 12 and d.day in (24, 25, 26, 31)) else 0
        is_payday_window = 1 if d.day in (25, 26, 27, 28) else 0

        rows.append(
            (
                d.isoformat(),
                dow,
                week_of_year,
                month,
                is_holiday,
                is_payday_window,
                season_for_month(month),
            )
        )
        d += timedelta(days=1)

    conn.executemany(
        """
        INSERT OR IGNORE INTO dim_calendar
        (date, day_of_week, week_of_year, month, is_holiday, is_payday_window, season)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        seed_segments(conn)

        today = date.today()
        start = today - timedelta(days=180)
        seed_calendar(conn, start=start, end=today)

        conn.commit()
        print(f"✅ Seeded dim_segment and dim_calendar for {start.isoformat()} to {today.isoformat()}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
