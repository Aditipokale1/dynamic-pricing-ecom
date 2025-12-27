-- sql/recommendations_schema.sql
CREATE TABLE IF NOT EXISTS pricing_recommendations (
  run_date TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  segment_id TEXT NOT NULL,

  recommended_price REAL NOT NULL,
  expected_units REAL NOT NULL,
  expected_profit REAL NOT NULL,

  reasons TEXT, -- comma-separated reason codes
  model_name TEXT NOT NULL,
  policy_version TEXT NOT NULL,

  PRIMARY KEY (run_date, sku_id, segment_id)
);
