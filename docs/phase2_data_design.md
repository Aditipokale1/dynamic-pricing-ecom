# Phase 2 — E-commerce Data Design (Tables + Fields)

## Grain (most important)
- Pricing decision grain: SKU × Segment × Day
- All fact tables should align to this grain or be easily aggregated to it.

## Dimensions

### dim_sku
Primary key: sku_id
Fields:
- sku_id (TEXT, PK)
- category (TEXT)
- brand (TEXT)
- unit_cost (REAL)                  -- > 0
- msrp (REAL)                       -- nullable
- map_price (REAL)                  -- nullable
- launch_date (DATE)
- is_kvi (INTEGER 0/1)

### dim_segment
Primary key: segment_id
Fields:
- segment_id (TEXT, PK)             -- e.g., "new", "returning", "price_sensitive", "high_value"
- description (TEXT)

### dim_calendar
Primary key: date
Fields:
- date (DATE, PK)
- day_of_week (INTEGER)
- week_of_year (INTEGER)
- month (INTEGER)
- is_holiday (INTEGER 0/1)
- is_payday_window (INTEGER 0/1)
- season (TEXT)

## Facts

### fact_traffic
Grain: sku_id × segment_id × date
Primary key: (sku_id, segment_id, date)
Fields:
- sku_id (TEXT)
- segment_id (TEXT)
- date (DATE)
- sessions (INTEGER)                 -- >= 0
- views (INTEGER)                    -- >= 0
- add_to_cart (INTEGER)              -- >= 0

### fact_prices_shown
Grain: sku_id × segment_id × date
Primary key: (sku_id, segment_id, date)
Fields:
- sku_id (TEXT)
- segment_id (TEXT)
- date (DATE)
- price_shown (REAL)                 -- > 0
- promo_active (INTEGER 0/1)
- discount_pct_vs_msrp (REAL)        -- can be negative if price > msrp, but we’ll usually keep <= 0 in clean data
- competitor_price (REAL)            -- nullable
- logging_propensity (REAL)          -- in (0,1]

### fact_sales
Grain: sku_id × segment_id × date
Primary key: (sku_id, segment_id, date)
Fields:
- sku_id (TEXT)
- segment_id (TEXT)
- date (DATE)
- orders (INTEGER)                   -- >= 0
- units_sold (INTEGER)               -- >= 0
- revenue (REAL)                     -- >= 0
- profit (REAL)                      -- can be negative in edge cases, but typically >= 0

### fact_inventory
Grain: sku_id × date
Primary key: (sku_id, date)
Fields:
- sku_id (TEXT)
- date (DATE)
- on_hand (INTEGER)                  -- >= 0
- inbound (INTEGER)                  -- >= 0
- stockout_flag (INTEGER 0/1)
- days_of_cover (REAL)               -- nullable early, computed later

## Data Contracts (validation rules)
- price_shown > 0
- unit_cost > 0
- sessions/views/add_to_cart >= 0
- orders/units_sold >= 0
- logging_propensity in (0, 1]
- competitor_price missing rate should be below a threshold (e.g., < 10%)
- No duplicate rows at the declared grain (enforce with PKs)
