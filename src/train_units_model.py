# src/train_units_model.py
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor

TRAIN_PATH = "data/train.csv"
VALID_PATH = "data/valid.csv"

TARGET = "units_sold"
DROP_COLS = ["sku_id", "segment_id", "date"]  # IDs/time not used in baseline

def prepare(df: pd.DataFrame):
    y = df[TARGET].astype(float)
    X = df.drop(columns=[TARGET] + DROP_COLS)

    # fill missing numeric values (lags are missing on first day per SKU×segment)
    X = X.fillna(0)

    # ensure all columns are numeric
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    return X, y

def main():
    train = pd.read_csv(TRAIN_PATH)
    valid = pd.read_csv(VALID_PATH)

    X_train, y_train = prepare(train)
    X_valid, y_valid = prepare(valid)

    model = HistGradientBoostingRegressor(
        learning_rate=0.08,
        max_depth=6,
        max_iter=200,
        random_state=42
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_valid)

    mae = mean_absolute_error(y_valid, pred)
    rmse = mean_squared_error(y_valid, pred) ** 0.5

    print("✅ Model trained")
    print(f"Validation MAE:  {mae:.4f}")
    print(f"Validation RMSE: {rmse:.4f}")

    # quick sanity: average actual vs predicted
    print(f"Avg actual units: {y_valid.mean():.4f}")
    print(f"Avg pred units:   {pred.mean():.4f}")

if __name__ == "__main__":
    main()
