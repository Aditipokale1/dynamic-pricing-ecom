# Phase 1 — E-commerce Dynamic Pricing Problem Definition

## Scenario
We are building a daily dynamic pricing system for a mid-size e-commerce retailer.

- SKU count: ~600 SKUs
- Categories: electronics, home, beauty, sports, toys
- Decision frequency: daily
- Decision unit (later phases): SKU × customer segment × day

## Objective
Maximize expected profit per SKU/segment/day:

Expected Profit(price) = (price - unit_cost) × E[units | price, context]

Why profit:
- Profit aligns with true business value (unlike GMV which can be inflated by discounting).
- Encourages discounting only when it increases expected profit.

## Guardrails (Business Constraints)

### Price floor / margin floor
- Minimum gross margin floor: 20%
- Floor price = unit_cost × (1 + 0.20)
- If a promo is active, price is locked to promo price (promo can override normal rules).

### Price ceiling (MSRP) and MAP
- Price must not exceed MSRP (when MSRP is available).
- If MAP is defined, price must be ≥ MAP.

### Max price change per day (inventory-aware)
- Default daily price change limit: ±10% vs yesterday’s price.
- Low stock: tighten to ±5%.
- Overstock: allow up to -20% downward movement (discounting more aggressively).

### Promo rules
- If promo is active, price is locked to the promo price.

### Competitor constraint (KVI only)
For Key Value Items (KVI):
- Do not exceed competitor price by more than +3%.
  price ≤ competitor_price × 1.03

### Customer trust (weekly volatility)
In any rolling 7-day window:
- No more than 3 changes larger than 5%.
(Implemented later when price history is available.)

### Inventory rules
Inventory position affects how aggressive price changes can be:
- Low stock: days of cover < 7
- Overstock: days of cover > 45

## Outputs from the pricing engine (later phases)
For each SKU × segment × day:
- recommended price
- expected profit/revenue deltas
- constraint reason codes (e.g., PROMO_LOCK, MARGIN_FLOOR_APPLIED, COMPETITOR_CAP_APPLIED)
