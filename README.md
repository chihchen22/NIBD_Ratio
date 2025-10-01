# Dynamic NIBD Ratio Model

Complete, reproducible analysis and scenario tooling for the dynamic Non-Interest-Bearing Deposits (NIBD) ratio and its Net Interest Income (NII) sensitivity. The entire workflow is implemented in a single script: `Dynamic_NIBD_Complete_Analysis.py`.

## Quick start (Windows/PowerShell)

1. Ensure you have Python 3.10+ (this repo uses a venv already if opened in VS Code)
2. From the repo root, run the full analysis with exports enabled:

```powershell
# Uses the workspace virtual environment if opened in VS Code
C:/Users/deech/Github/NIBD_Ratio/.venv/Scripts/python.exe .\Dynamic_NIBD_Complete_Analysis.py --export --export-dir .\exports
```

Optional flags:

- `--csv` Path to the input CSV (default: `NIBD_ratio_v2.csv`)
- `--shock-bp` Parallel rate shock in bp for the scenario (default: 300)
- `--total-deposits-bn` Total deposits in billions for the representative bank (default: 40.0)
- `--rate-differential` Rate differential between IB and NIBD, decimal (default: 0.055)
- `--static-nii` Static asset-side NII benefit in millions to compute net (default: 150.0)
- `--export` Write CSV/JSON and save plots
- `--export-dir` Output directory for exports (default: `./exports`)

## Inputs

- `NIBD_ratio_v2.csv` with the following required columns: `QtrEndDt` (or `Date`), `ALLCB_NIBD`, `12MA_FEFF` (or `FEFF`), `FBS_GDP`, and either `SOFR10Y` & `SOFR2Y` or `10Y_SOFR` & `2Y_SOFR` (used to compute `10Y_2Y`).

## Outputs (when `--export` is used)

- `exports/monthly_transmission.csv`
  - 12-month case study transmission table for the provided shock.
  - Columns: `Month`, `MA_Base_bp`, `Delta_MA_bp`, `NIBD_Delta_pp`, `Outflow_M`, `NII_Impact_M`.
- `exports/scenario_summary.json`
  - Single-file summary containing scenario parameters, model summaries, diagnostics, structured coefficients and fit, out-of-sample metrics, unit-root results, and VIF.
- `exports/dynamic_nibd_key_visuals.png` and `exports/correlation_heatmap.png`

Key scenario metrics (from `scenario_summary.json`):

- Fed LR multiplier: `fed_lr_multiplier` (pp per 1.00 change in 12MA_FEFF)
- Corrected first-year dynamic NII: `corrected_first_year_nii_m` (millions)
- Naive first-year dynamic NII: `naive_first_year_nii_m` (millions)
- Total deposit reallocation: `total_reallocation_m` (millions)
- Average monthly outflow: `avg_monthly_outflow_m` (millions)
- Net NII (Corrected): `net_nii_corrected_m` (millions, if static provided)
- Net NII (Naive): `net_nii_naive_m` (millions, if static provided)

## scenario_summary.json schema

Top-level keys:

- `shock_bp` (int): Parallel rate shock in basis points.
- `total_deposits_bn` (number): Total deposits in billions.
- `rate_differential` (number): Rate differential (decimal) between IB and NIBD.
- `static_nii_m` (number|null): Static asset-side NII benefit in millions if provided.
- `fed_lr_multiplier` (number): Long-run multiplier of 12MA Fed Funds on NIBD (pp per 1.00 change).
- `corrected_first_year_nii_m` (number): Corrected first-year dynamic NII impact (millions), accounting for 12-month MA transmission.
- `naive_first_year_nii_m` (number): Naive first-year dynamic NII (millions) assuming immediate full-year application.
- `total_reallocation_m` (number): Total deposit reallocation over the year (millions); equals the sum of `Outflow_M` in `monthly_transmission.csv`.
- `avg_monthly_outflow_m` (number): Average monthly deposit reallocation (millions); mean of `Outflow_M` across the 12 months.
- `net_nii_corrected_m` (number|null): Static minus corrected dynamic NII (if static provided).
- `net_nii_naive_m` (number|null): Static minus naive dynamic NII (if static provided).

Models block:

- `models.ardl`:
  - `summary_text` (string): OLS summary for ARDL(1,1,1,1) equivalent.
  - `diagnostics` (object): Ljung–Box, Breusch–Pagan, Jarque–Bera, RESET, Durbin–Watson.
  - `structured` (object):
    - `coefficients` (object of number): per-parameter coefficients
    - `std_errors` (object of number)
    - `t_stats` (object of number)
    - `p_values` (object of number)
    - `conf_int_95` (object): `{ param: { lower: number, upper: number } }`
    - `fit` (object): `{ r2, adj_r2, aic, bic, llf, f_stat, f_pvalue, nobs, df_model, df_resid }`
- `models.ecm`:
  - `static_summary_text` (string): Long-run static regression summary.
  - `ecm_summary_text` (string): ECM (differences + lagged ECT) summary.
  - `diagnostics` (object): Same test set as ARDL.
  - `static_structured` (object): Same shape as `models.ardl.structured`.
  - `ecm_structured` (object): Same shape as `models.ardl.structured`.

Validation block:

- `validation.ardl` and `validation.ecm` (object): `{ MAE, RMSE, MAPE, Theil_U }`

Unit-root block:

- `unit_root` (object):
  - For each variable (e.g., `ALLCB_NIBD`, `12MA_FEFF`, `FBS_GDP`, `10Y_2Y`):
    - `adf_stat` (number), `adf_pval` (number)
    - `kpss_stat` (number), `kpss_pval` (number)
    - `integration_order` (string): One of `"I(0)"`, `"I(1)"`, or `"I(1) borderline"`

VIF block:

- `vif` (array): Each entry `{ variable: string, vif: number, status: string }`

## methodology highlights

- ARDL(1,1,1,1) estimated via an explicit OLS lagged design; long-run multipliers derived as `(b0 + b1) / (1 - φ1)`.
- ECM via Engle–Granger: static long-run regression → ADF on residuals (regression='n') → ECM with differences + lagged ECT.
- Diagnostics: Ljung–Box (4 lags), Breusch–Pagan, Jarque–Bera, RESET (use_f=True), Durbin–Watson.
- Scenario transmission: Proper 12-month moving-average pass-through applied to compute first-year dynamic NII vs naive.

## troubleshooting

- If you see missing Python modules, ensure the virtual environment is active in VS Code, or install dependencies: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `scikit-learn`, `statsmodels`.
- If exports are empty, pass `--export` and verify the `--export-dir` path exists or can be created.
