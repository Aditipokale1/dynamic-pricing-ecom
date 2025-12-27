-- sql/run_summary_schema.sql
CREATE TABLE IF NOT EXISTS pricing_run_summary (
  run_date TEXT PRIMARY KEY,

  n_recommendations INTEGER NOT NULL,

  avg_recommended_price REAL NOT NULL,
  total_expected_units REAL NOT NULL,
  total_expected_profit REAL NOT NULL,

  -- reason code hit counts
  n_none INTEGER NOT NULL,
  n_max_daily_change INTEGER NOT NULL,
  n_competitor_cap INTEGER NOT NULL,
  n_margin_floor INTEGER NOT NULL,
  n_map_floor INTEGER NOT NULL,

  -- reason code hit rates
  r_none REAL NOT NULL,
  r_max_daily_change REAL NOT NULL,
  r_competitor_cap REAL NOT NULL,
  r_margin_floor REAL NOT NULL,
  r_map_floor REAL NOT NULL
);
