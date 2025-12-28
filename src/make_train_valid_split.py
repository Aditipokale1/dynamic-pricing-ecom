# src/make_train_valid_split.py
import sqlite3
from pathlib import Path

DB_PATH = "data/pricing.db"
OUT_TRAIN = Path("data/train.csv")
OUT_VALID = Path("data/valid.csv")

VALID_DAYS = 28

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # Get max date in feature table
        max_date = cur.execute("SELECT MAX(date) FROM feature_sku_segment_day").fetchone()[0]
        if max_date is None:
            raise ValueError("feature_sku_segment_day is empty")

        # Finding split date = max_date - VALID_DAYS + 1 (inclusive window)
        # SQLite date arithmetic:
        split_date = cur.execute(
            "SELECT date(?, '-' || ? || ' days')",
            (max_date, VALID_DAYS - 1),
        ).fetchone()[0]

        print(f"Max date:   {max_date}")
        print(f"Valid from: {split_date} (last {VALID_DAYS} days)")
        print("Exporting CSVs...")

        # Export train
        train_rows = cur.execute("""
            SELECT *
            FROM feature_sku_segment_day
            WHERE date < ?
            ORDER BY date
        """, (split_date,))

        # Writing header + rows manually
        colnames = [d[0] for d in train_rows.description]
        OUT_TRAIN.parent.mkdir(parents=True, exist_ok=True)

        with OUT_TRAIN.open("w", encoding="utf-8") as f:
            f.write(",".join(colnames) + "\n")
            for row in train_rows:
                f.write(",".join("" if v is None else str(v) for v in row) + "\n")

        # Exporting valid
        valid_rows = cur.execute("""
            SELECT *
            FROM feature_sku_segment_day
            WHERE date >= ?
            ORDER BY date
        """, (split_date,))

        with OUT_VALID.open("w", encoding="utf-8") as f:
            f.write(",".join(colnames) + "\n")
            for row in valid_rows:
                f.write(",".join("" if v is None else str(v) for v in row) + "\n")

        # Printing counts
        n_train = cur.execute("SELECT COUNT(*) FROM feature_sku_segment_day WHERE date < ?", (split_date,)).fetchone()[0]
        n_valid = cur.execute("SELECT COUNT(*) FROM feature_sku_segment_day WHERE date >= ?", (split_date,)).fetchone()[0]
        print(f" Train rows: {n_train}")
        print(f" Valid rows: {n_valid}")
        print(f" Wrote: {OUT_TRAIN} and {OUT_VALID}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
