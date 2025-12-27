# src/db_init.py
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path("sql/schema.sql")
DB_PATH = Path("data/pricing.db")


def main():
    # Ensure data/ exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

    print(f"✅ Database created/updated at: {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()
