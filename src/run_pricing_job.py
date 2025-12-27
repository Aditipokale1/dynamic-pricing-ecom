# src/run_pricing_job.py
import sqlite3
from pathlib import Path
import yaml
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.pricing.rules import Context, apply_guardrails
from src.pricing.objective import ObjectiveInputs, expected_profit

DB_PATH = "data/pricing.db"
POLICY_PATH = Path("src/config/pricing_policy.yaml")
RECO_SCHEMA_PATH = Path("sql/recommendations_schema.sql")

# Candidate action space (same as logging buckets for now)
CANDIDATE_MULTS = [0.90, 0.95, 1.00, 1.05, 1.10]

TARGET = "units_sold"
ID_COLS = ["sku_id", "segment_id", "date"]
LABEL_LEAK_COLS = ["orders", "revenue", "profit"]  # do NOT use these as features


def load_policy() -> dict:
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_reco_table(conn: sqlite3.Connection) -> None:
    conn.executescript(RECO_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def train_units_model_no_leak() -> tuple[HistGradientBoostingRegressor, list[str]]:
    """
    Train on train.csv, predicting units_sold.
    IMPORTANT: do not use outcome-like columns (orders/revenue/profit) as features.
    """
    train = pd.read_csv("data/train.csv")

    y = train[TARGET].astype(float)
    X = train.drop(columns=[TARGET] + ID_COLS, errors="ignore")

    # remove label leakage columns if present
    X = X.drop(columns=[c for c in LABEL_LEAK_COLS if c in X.columns], errors="ignore")

    X = X.fillna(0)
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


def fetch_run_rows(conn: sqlite3.Connection, run_date: str):
    """
    Fetch everything needed for pricing for run_date at SKU×segment grain:
    - base features from feature table
    - sku context: cost/msrp/map/is_kvi
    - competitor & promo from fact_prices_shown
    - yesterday_price from fact_prices_shown (same sku+segment, date-1)
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT
          f.sku_id, f.segment_id, f.date,

          -- base features
          f.price_shown, f.discount_pct_vs_msrp, f.price_index_vs_comp,
          f.price_change_pct_1d, f.price_rolling_avg_7d,
          f.sessions, f.views, f.add_to_cart, f.sessions_lag_1d,
          f.on_hand, f.inbound, f.stockout_flag, f.days_of_cover,
          f.low_stock_flag, f.overstock_flag,

          -- sku context
          s.unit_cost, s.msrp, s.map_price, s.is_kvi,

          -- logged context
          p.competitor_price, p.promo_active,

          -- yesterday price for guardrails + price_change recompute
          (SELECT p2.price_shown
           FROM fact_prices_shown p2
           WHERE p2.sku_id = p.sku_id
             AND p2.segment_id = p.segment_id
             AND p2.date = date(p.date, '-1 day')
          ) AS yesterday_price

        FROM feature_sku_segment_day f
        JOIN dim_sku s ON f.sku_id = s.sku_id
        JOIN fact_prices_shown p
          ON f.sku_id = p.sku_id AND f.segment_id = p.segment_id AND f.date = p.date
        WHERE f.date = ?
        ORDER BY f.sku_id, f.segment_id
    """, (run_date,))
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows


def make_model_row(base: dict, feature_cols: list[str]) -> pd.DataFrame:
    """
    Build a single-row DataFrame aligned to model feature columns.
    base should contain ALL potential feature fields; we will select/reindex.
    """
    df = pd.DataFrame([base])
    df = df.reindex(columns=feature_cols, fill_value=0)
    df = df.fillna(0)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def main():
    policy = load_policy()
    model, feature_cols = train_units_model_no_leak()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_reco_table(conn)

        run_date = conn.execute("SELECT MAX(date) FROM feature_sku_segment_day").fetchone()[0]
        if run_date is None:
            raise ValueError("feature_sku_segment_day is empty")

        print(f"Run date: {run_date}")

        cols, rows = fetch_run_rows(conn, run_date)
        print(f"Rows to price: {len(rows)}")

        # metadata
        model_name = "HistGradientBoostingRegressor_units_v1_noleak"
        policy_version = str(policy.get("policy_version", "unknown"))

        # replace existing recos for this run_date (idempotent)
        conn.execute("DELETE FROM pricing_recommendations WHERE run_date = ?", (run_date,))
        conn.commit()

        inserts = []

        for r in rows:
            rec = dict(zip(cols, r))

            sku_id = rec["sku_id"]
            segment_id = rec["segment_id"]

            unit_cost = float(rec["unit_cost"])
            msrp = float(rec["msrp"]) if rec["msrp"] is not None else None
            map_price = float(rec["map_price"]) if rec["map_price"] is not None else None
            is_kvi = bool(rec["is_kvi"])
            competitor_price = float(rec["competitor_price"]) if rec["competitor_price"] is not None else None
            promo_active = bool(rec["promo_active"])
            days_of_cover = float(rec["days_of_cover"]) if rec["days_of_cover"] is not None else None
            yesterday_price = float(rec["yesterday_price"]) if rec["yesterday_price"] is not None else None

            if msrp is None or msrp <= 0:
                # skip pathological rows
                continue

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
                final_price = float(ruled.final_price)

                # Build candidate feature row based on existing feature fields (not labels)
                base_features = {
                    # price features
                    "price_shown": final_price,
                    "discount_pct_vs_msrp": (1.0 - (final_price / msrp)) if msrp else 0.0,
                    "price_index_vs_comp": (final_price / competitor_price) if competitor_price else 0.0,
                    "price_change_pct_1d": ((final_price - yesterday_price) / yesterday_price)
                                          if (yesterday_price and yesterday_price > 0) else 0.0,
                    "price_rolling_avg_7d": float(rec["price_rolling_avg_7d"]),

                    # demand
                    "sessions": int(rec["sessions"]),
                    "views": int(rec["views"]),
                    "add_to_cart": int(rec["add_to_cart"]),
                    "sessions_lag_1d": int(rec["sessions_lag_1d"]) if rec["sessions_lag_1d"] is not None else 0,

                    # inventory
                    "on_hand": int(rec["on_hand"]),
                    "inbound": int(rec["inbound"]),
                    "stockout_flag": int(rec["stockout_flag"]),
                    "days_of_cover": days_of_cover if days_of_cover is not None else 0.0,
                    "low_stock_flag": int(rec["low_stock_flag"]),
                    "overstock_flag": int(rec["overstock_flag"]),
                }

                X = make_model_row(base_features, feature_cols)
                expected_units = float(model.predict(X)[0])
                exp_profit = expected_profit(ObjectiveInputs(
                    price=final_price, unit_cost=unit_cost, expected_units=expected_units
                ))

                cand = {
                    "final_price": final_price,
                    "expected_units": expected_units,
                    "expected_profit": exp_profit,
                    "reasons": ruled.reasons,
                }

                if best is None or cand["expected_profit"] > best["expected_profit"]:
                    best = cand

            if best is None:
                continue

            inserts.append((
                run_date, sku_id, segment_id,
                best["final_price"],
                best["expected_units"],
                best["expected_profit"],
                ",".join(best["reasons"]),
                model_name,
                policy_version
            ))

        conn.executemany(
            """
            INSERT OR REPLACE INTO pricing_recommendations
            (run_date, sku_id, segment_id, recommended_price, expected_units, expected_profit,
             reasons, model_name, policy_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            inserts
        )
        conn.commit()

        print(f"✅ Wrote {len(inserts)} recommendations into pricing_recommendations for {run_date}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
