# Phase 4 — Logged Pricing Policy (Offline Evaluation Setup)

## Why we need a logged policy
To evaluate a new pricing policy offline, we need:
- the price that was shown historically (action)
- the context at decision time (features)
- the propensity (probability) of choosing that action under the logging policy
- the observed outcome (orders/units/profit)

This enables IPS / Doubly Robust evaluation later.

## Action space
We use discrete multiplier buckets applied to MSRP:

Multipliers = [0.90, 0.95, 1.00, 1.05, 1.10]

price_shown = max(unit_cost * 1.05, msrp * multiplier)

Promo days can override the shown price (promo_active=1). Promo events are logged.

## Context logged per SKU × Segment × Day
Stored across tables at the same grain:
- Traffic: sessions, views, add_to_cart (fact_traffic)
- Price shown: price_shown, promo_active, discount_pct_vs_msrp, competitor_price, logging_propensity (fact_prices_shown)
- Outcome: orders, units_sold, revenue, profit (fact_sales)
- Inventory availability: stockout_flag, days_of_cover (fact_inventory at sku×day)

## Propensity
logging_propensity is the probability of the chosen multiplier under the logging policy.
It is computed by a softmax over the multiplier scores, influenced by:
- segment bias (e.g., price_sensitive favors lower multipliers)
- KVI bias (key items slightly favor lower multipliers)

Propensity values must be in (0,1].

## Required data contracts for offline eval
- Every row in fact_prices_shown must have logging_propensity in (0,1]
- No duplicates at SKU × Segment × Day grain
- price_shown > 0
- Outcomes present for every logged price (fact_sales aligned to same grain)
