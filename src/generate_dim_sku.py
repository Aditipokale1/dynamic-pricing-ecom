# src/generate_dim_sku.py
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = "data/pricing.db"

CATEGORIES = {
    "electronics": ["Voltix", "NovaTech", "ZenWare"],
    "home": ["Hearthly", "RoomRoot", "CozyCraft"],
    "beauty": ["GlowLab", "PurePetal", "LuxeLeaf"],
    "sports": ["AeroActive", "PeakPro", "StrideCo"],
    "toys": ["PlayForge", "KiddoWorks", "BrightBee"],
}

def rand_launch_date(rng: random.Random) -> str:
    # Launch sometime in last 2 years
    days_ago = rng.randint(0, 730)
    d = date.today() - timedelta(days=days_ago)
    return d.isoformat()

def generate_skus(n: int = 600, seed: int = 42):
    rng = random.Random(seed)
    rows = []

    categories = list(CATEGORIES.keys())

    for i in range(1, n + 1):
        category = rng.choice(categories)
        brand = rng.choice(CATEGORIES[category])

        # Cost distribution by category (roughly)
        if category == "electronics":
            unit_cost = rng.uniform(20, 300)
            markup = rng.uniform(1.25, 1.80)
        elif category == "home":
            unit_cost = rng.uniform(5, 120)
            markup = rng.uniform(1.40, 2.50)
        elif category == "beauty":
            unit_cost = rng.uniform(1, 40)
            markup = rng.uniform(2.0, 5.0)
        elif category == "sports":
            unit_cost = rng.uniform(8, 150)
            markup = rng.uniform(1.50, 2.80)
        else:  # toys
            unit_cost = rng.uniform(2, 80)
            markup = rng.uniform(1.60, 3.50)

        msrp = unit_cost * markup

        # MAP: sometimes present (esp electronics), usually below MSRP but above cost
        map_price = None
        if category == "electronics" and rng.random() < 0.55:
            map_price = max(unit_cost * 1.15, msrp * rng.uniform(0.75, 0.90))
        elif rng.random() < 0.10:
            map_price = max(unit_cost * 1.10, msrp * rng.uniform(0.70, 0.92))

        # KVI flag: ~15% of SKUs are key items
        is_kvi = 1 if rng.random() < 0.15 else 0

        sku_id = f"{category[:4].upper()}-{i:04d}"
        launch_date = rand_launch_date(rng)

        # Round money values to 2 decimals
        unit_cost = round(unit_cost, 2)
        msrp = round(msrp, 2)
        if map_price is not None:
            map_price = round(map_price, 2)

        rows.append((sku_id, category, brand, unit_cost, msrp, map_price, launch_date, is_kvi))

    return rows

def main():
    rows = generate_skus(n=600, seed=42)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executemany(
            """
            INSERT OR REPLACE INTO dim_sku
            (sku_id, category, brand, unit_cost, msrp, map_price, launch_date, is_kvi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows
        )
        conn.commit()
        print(f"✅ Inserted {len(rows)} rows into dim_sku")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
