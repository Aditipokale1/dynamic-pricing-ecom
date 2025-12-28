# Phase 1 — E-commerce Dynamic Pricing Problem Definition

## Scenario
We are building a **daily dynamic pricing system** for a **mid-size e-commerce retailer**.

- **Scale:** ~600 SKUs  
- **Categories:** Electronics, Home, Beauty, Sports, Toys  
- **Decision frequency:** Daily  
- **Decision unit:** **SKU × Customer Segment × Day**  

### Customer segments (example)
We model pricing impact separately for different customer types:
- **New customers**: less loyal, often more price-sensitive  
- **Returning customers**: higher trust, less elastic  
- **Price-sensitive**: higher conversion response to discounts  
- **High-value**: lower elasticity, higher willingness to pay  

---

## Objective (Optimization Target)
We choose prices to **maximize expected profit** per SKU–segment–day:

**Expected Profit(price) = (price − unit_cost) × E[units | price, context]**

### Why profit (vs GMV)
- Profit directly reflects business value (GMV can be inflated by discounting).
- Encourages discounting only when it increases expected profit, not just volume.
- Aligns with retail pricing team KPIs (margin + contribution).

---

## Guardrails (Business Constraints)

### 1) Margin floor / Price floor
- **Minimum gross margin:** 20%  
- **Floor price:** `unit_cost × (1 + 0.20)`  
- **Exception:** If a **promo is active**, the price is **locked** to the promo price (promo can override normal rules).

### 2) MSRP ceiling + MAP floor
- **Price ceiling:** price must not exceed **MSRP** (if MSRP is defined).
- **MAP rule:** if **MAP** is defined, price must be **≥ MAP**.

### 3) Max daily price movement (inventory-aware)
Default max day-to-day movement (vs yesterday’s price):
- **Normal:** ±10%  
- **Low stock:** tighten to **±5%**  
- **Overstock:** allow more aggressive discounting down to **−20%**  

### 4) Promo rules
- If **promo_active = true**, price is **locked** to the promo price and guardrails do not adjust it.

### 5) Competitor constraint (KVI items only)
For **Key Value Items (KVI)** where competitive pricing matters:
- Do not exceed competitor price by more than **+3%**  
- Constraint: `price ≤ competitor_price × 1.03`

### 6) Customer trust rule (weekly volatility)
To avoid “price whiplash” that harms customer trust:
- In any rolling 7-day window: **no more than 3 price changes > 5%**  
- (This is applied once we have enough historical price data.)

### 7) Inventory definitions
Inventory position determines how aggressive we can be:
- **Low stock:** days of cover `< 7`
- **Overstock:** days of cover `> 45`

---

## KPIs (what we monitor)
Primary:
- **Expected profit** (primary KPI)
- **Expected units**

Secondary:
- Average price level
- Discount rate vs MSRP
- Price index vs competitor (for KVI items)
- Guardrail hit rate (how often constraints bind)

---

## Pricing engine outputs
For each **SKU × Segment × Day**, the system produces:
- **recommended_price**
- **expected_units**, **expected_profit**
- **reason codes** explaining constraints applied  
  Example: `PROMO_LOCK`, `MARGIN_FLOOR_APPLIED`, `COMPETITOR_CAP_APPLIED`, `MAX_DAILY_CHANGE_CLAMPED`
