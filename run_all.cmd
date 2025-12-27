@echo off
REM Rebuild DB + generate data + features + train + run pricing + summary

python src\db_init.py
python src\db_seed.py
python src\generate_dim_sku.py

python src\generate_fact_inventory.py
python src\generate_fact_traffic.py
python src\generate_fact_prices_shown.py
python src\generate_fact_sales.py

python src\validate_data.py

python src\build_features.py
python src\validate_features.py

python src\train_units_model.py

python -m src.run_pricing_job
python -m src.build_run_summary

echo.
echo ✅ Done. DB is in data\pricing.db
pause
