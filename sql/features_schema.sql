-- sql/features_schema.sql
CREATE TABLE IF NOT EXISTS feature_sku_segment_day (
  sku_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,
  date TEXT NOT NULL,

  -- price features
  price_shown REAL NOT NULL,
  discount_pct_vs_msrp REAL,
  price_index_vs_comp REAL,
  price_change_pct_1d REAL,
  price_rolling_avg_7d REAL,

  -- demand features
  sessions INTEGER NOT NULL,
  views INTEGER NOT NULL,
  add_to_cart INTEGER NOT NULL,
  sessions_lag_1d INTEGER,

  -- inventory features
  on_hand INTEGER NOT NULL,
  inbound INTEGER NOT NULL,
  stockout_flag INTEGER NOT NULL,
  days_of_cover REAL,
  low_stock_flag INTEGER NOT NULL,
  overstock_flag INTEGER NOT NULL,

  -- labels (for training)
  orders INTEGER NOT NULL,
  units_sold INTEGER NOT NULL,
  revenue REAL NOT NULL,
  profit REAL NOT NULL,

  PRIMARY KEY (sku_id, segment_id, date)
);
