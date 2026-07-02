# Vendored Risk Assets

This directory contains the minimum vendored assets copied from the upstream `ml_risk_control` project for local integration inside this repository.

Current contents:

- `artifacts/xgboost/xgboost_credit_risk.joblib`: reusable XGBoost model bundle
- `artifacts/xgboost/feature_schema.json`: feature contract metadata
- `artifacts/xgboost/run_summary.json`: saved run metadata
- `artifacts/xgboost/threshold_selection_report.json`: saved threshold-selection metadata
- `artifacts/xgboost/cost_analysis_report.json`: saved cost-threshold metadata
- `artifacts/xgboost/calibration_report.json`: saved calibration metadata

These files are treated as vendored source material for the local `RISK` integration path.

