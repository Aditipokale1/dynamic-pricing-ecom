# src/demo_recommend_one_price.py
import sqlite3
import yaml
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.pricing.rules import Context, apply_guardrails
from src.pricing.objective import ObjectiveInputs, expected_profit

DB_PATH = "data/pricing.db"
POLICY_PATH = "src/config/pricing_policy.yaml"

# candidate multipliers (business-realistic discrete set)
CANDIDATE_MULTS = [0.90, 0.95, 1.00, 1.05, 1.10]

TARGET = "units_sold"
DROP_COLS = ["sku_id", "segment_id", "date"]

def load_policy():
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def train_model():
    train = pd.read_csv("data/train.csv")
    X = train.drop(columns=[TARGET] + DROP_COLS).fillna(0)
    y = train[TARGET].astype(float)

    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    model = HistGradientBoostingRegressor(
        learning_rate=0.08,
        max_depth=6,
        max_iter=200,
        random_state=42
    )
    model.fit(X, y)
    return model, list(X.columns)

def fetch_one_valid_row(conn):
    # Take one row from the last day for a KVI if possible
    cur = conn.cursor()
    cur.execute("""
        SELECT f.sku_id, f.segment_id, f.date
        FROM feature_sku_segment_day f
        JOIN dim_sku s ON f.sku_id = s.sku_id
        WHERE f.date = (SELECT MAX(date) FROM feature_sku_segment_day)
        ORDER BY s.is_kvi DESC, f.sku_id
        LIMIT 1
    """)
    return cur.fetchone()  # (sku_id, segment_id, date)

def fetch_context_and_features(conn, sku_id, segment_id, date_str):
    cur = conn.cursor()

    # context fields for guardrails
    cur.execute("""
        SELECT
          s.unit_cost, s.msrp, s.map_price, s.is_kvi,
          p.competitor_price, p.promo_active,
          i.days_of_cover,
          p.price_shown,
          (SELECT p2.price_shown
           FROM fact_prices_shown p2
           WHERE p2.sku_id=p.sku_id AND p2.segment_id=p.segment_id
             AND p2.date = date(p.date, '-1 day')
          ) AS yesterday_price
        FROM dim_sku s
        JOIN fact_prices_shown p
          ON s.sku_id=p.sku_id
        JOIN fact_inventory i
          ON s.sku_id=i.sku_id AND p.date=i.date
        WHERE p.sku_id=? AND p.segment_id=? AND p.date=?
    """, (sku_id, segment_id, date_str))
    row = cur.fetchone()
    if row is None:
        raise ValueError("Could not fetch context row")

    unit_cost, msrp, map_price, is_kvi, comp_price, promo_active, doc, price_today, y_price = row

    # feature row (for model input)
    df = pd.read_sql_query("""
        SELECT *
        FROM feature_sku_segment_day
        WHERE sku_id=? AND segment_id=? AND date=?
    """, conn, params=(sku_id, segment_id, date_str))

    return {
        "unit_cost": float(unit_cost),
        "msrp": float(msrp) if msrp is not None else None,
        "map_price": float(map_price) if map_price is not None else None,
        "is_kvi": bool(is_kvi),
        "competitor_price": float(comp_price) if comp_price is not None else None,
        "promo_active": bool(promo_active),
        "days_of_cover": float(doc) if doc is not None else None,
        "today_logged_price": float(price_today),
        "yesterday_price": float(y_price) if y_price is not None else None,
        "features_df": df,
    }

def make_model_features(features_df: pd.DataFrame, feature_cols: list):
    # drop ids + target-like columns if present
    drop = {"sku_id", "segment_id", "date"}
    X = features_df.drop(columns=[c for c in drop if c in features_df.columns]).copy()

    # remove labels if they exist
    for lbl in ["orders", "units_sold", "revenue", "profit"]:
        if lbl in X.columns:
            X = X.drop(columns=[lbl])

    X = X.fillna(0)
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    # align to training columns
    X = X.reindex(columns=feature_cols, fill_value=0)
    return X

def main():
    policy = load_policy()
    model, feature_cols = train_model()

    conn = sqlite3.connect(DB_PATH)
    try:
        sku_id, segment_id, date_str = fetch_one_valid_row(conn)
        payload = fetch_context_and_features(conn, sku_id, segment_id, date_str)

        unit_cost = payload["unit_cost"]
        msrp = payload["msrp"]
        map_price = payload["map_price"]
        is_kvi = payload["is_kvi"]
        competitor_price = payload["competitor_price"]
        promo_active = payload["promo_active"]
        days_of_cover = payload["days_of_cover"]
        yesterday_price = payload["yesterday_price"]

        # base feature row (we will modify price-dependent fields per candidate)
        base_df = payload["features_df"]

        print(f"SKU={sku_id} segment={segment_id} date={date_str}")
        print(f"Logged price today: {payload['today_logged_price']}")
        print(f"Cost={unit_cost:.2f} MSRP={msrp:.2f} MAP={map_price if map_price else 'None'} KVI={is_kvi}")
        print(f"Competitor={competitor_price:.2f} DaysOfCover={days_of_cover} YesterdayPrice={yesterday_price}")

        best = None

        for m in CANDIDATE_MULTS:
            raw_candidate = msrp * m

            ctx = Context(
                sku=sku_id,
                segment=segment_id,
                unit_cost=unit_cost,
                msrp=msrp,
                map_price=map_price,
                yesterday_price=yesterday_price,
                competitor_price=competitor_price,
                is_kvi=is_kvi,
                promo_active=promo_active,
                promo_price=None,
                days_of_cover=days_of_cover,
            )

            ruled = apply_guardrails(raw_candidate, ctx, policy)
            final_price = ruled.final_price

            # Create a temp feature row updated with candidate price
            temp = base_df.copy()
            temp.loc[:, "price_shown"] = final_price
            temp.loc[:, "discount_pct_vs_msrp"] = (1.0 - (final_price / msrp)) if msrp else 0.0
            temp.loc[:, "price_index_vs_comp"] = (final_price / competitor_price) if competitor_price else 0.0

            X = make_model_features(temp, feature_cols)
            expected_units = float(model.predict(X)[0])

            exp_profit = expected_profit(ObjectiveInputs(
                price=final_price,
                unit_cost=unit_cost,
                expected_units=expected_units
            ))

            cand = {
                "multiplier": m,
                "raw_candidate": raw_candidate,
                "final_price": final_price,
                "expected_units": expected_units,
                "expected_profit": exp_profit,
                "reasons": ruled.reasons
            }

            if best is None or cand["expected_profit"] > best["expected_profit"]:
                best = cand

        print("\n=== Recommendation ===")
        print(f"Recommended price: {best['final_price']:.2f}")
        print(f"From multiplier:   {best['multiplier']:.2f} (raw {best['raw_candidate']:.2f})")
        print(f"Expected units:    {best['expected_units']:.4f}")
        print(f"Expected profit:   {best['expected_profit']:.4f}")
        print(f"Reason codes:      {best['reasons']}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
