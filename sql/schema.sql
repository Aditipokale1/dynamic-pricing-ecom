-- sql/schema.sql
-- SQLite schema for dynamic pricing project

PRAGMA foreign_keys = ON;

-- =====================
-- Dimensions
-- =====================

CREATE TABLE IF NOT EXISTS dim_sku (
  sku_id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  brand TEXT NOT NULL,
  unit_cost REAL NOT NULL CHECK (unit_cost > 0),
  msrp REAL CHECK (msrp IS NULL OR msrp > 0),
  map_price REAL CHECK (map_price IS NULL OR map_price > 0),
  launch_date TEXT NOT NULL,
  is_kvi INTEGER NOT NULL CHECK (is_kvi IN (0,1))
);

CREATE TABLE IF NOT EXISTS dim_segment (
  segment_id TEXT PRIMARY KEY,
  description TEXT
);

CREATE TABLE IF NOT EXISTS dim_calendar (
  date TEXT PRIMARY KEY, -- YYYY-MM-DD
  day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  week_of_year INTEGER NOT NULL CHECK (week_of_year BETWEEN 1 AND 53),
  month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
  is_holiday INTEGER NOT NULL CHECK (is_holiday IN (0,1)),
  is_payday_window INTEGER NOT NULL CHECK (is_payday_window IN (0,1)),
  season TEXT
);

-- =====================
-- Facts
-- =====================

CREATE TABLE IF NOT EXISTS fact_traffic (
  sku_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,
  date TEXT NOT NULL,
  sessions INTEGER NOT NULL CHECK (sessions >= 0),
  views INTEGER NOT NULL CHECK (views >= 0),
  add_to_cart INTEGER NOT NULL CHECK (add_to_cart >= 0),
  PRIMARY KEY (sku_id, segment_id, date),
  FOREIGN KEY (sku_id) REFERENCES dim_sku(sku_id),
  FOREIGN KEY (segment_id) REFERENCES dim_segment(segment_id),
  FOREIGN KEY (date) REFERENCES dim_calendar(date)
);

CREATE TABLE IF NOT EXISTS fact_prices_shown (
  sku_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,
  date TEXT NOT NULL,
  price_shown REAL NOT NULL CHECK (price_shown > 0),
  promo_active INTEGER NOT NULL CHECK (promo_active IN (0,1)),
  discount_pct_vs_msrp REAL,
  competitor_price REAL CHECK (competitor_price IS NULL OR competitor_price > 0),
  logging_propensity REAL NOT NULL CHECK (logging_propensity > 0 AND logging_propensity <= 1),
  PRIMARY KEY (sku_id, segment_id, date),
  FOREIGN KEY (sku_id) REFERENCES dim_sku(sku_id),
  FOREIGN KEY (segment_id) REFERENCES dim_segment(segment_id),
  FOREIGN KEY (date) REFERENCES dim_calendar(date)
);

CREATE TABLE IF NOT EXISTS fact_sales (
  sku_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,
  date TEXT NOT NULL,
  orders INTEGER NOT NULL CHECK (orders >= 0),
  units_sold INTEGER NOT NULL CHECK (units_sold >= 0),
  revenue REAL NOT NULL CHECK (revenue >= 0),
  profit REAL NOT NULL,
  PRIMARY KEY (sku_id, segment_id, date),
  FOREIGN KEY (sku_id) REFERENCES dim_sku(sku_id),
  FOREIGN KEY (segment_id) REFERENCES dim_segment(segment_id),
  FOREIGN KEY (date) REFERENCES dim_calendar(date)
);

CREATE TABLE IF NOT EXISTS fact_inventory (
  sku_id TEXT NOT NULL,
  date TEXT NOT NULL,
  on_hand INTEGER NOT NULL CHECK (on_hand >= 0),
  inbound INTEGER NOT NULL CHECK (inbound >= 0),
  stockout_flag INTEGER NOT NULL CHECK (stockout_flag IN (0,1)),
  days_of_cover REAL,
  PRIMARY KEY (sku_id, date),
  FOREIGN KEY (sku_id) REFERENCES dim_sku(sku_id),
  FOREIGN KEY (date) REFERENCES dim_calendar(date)
);
