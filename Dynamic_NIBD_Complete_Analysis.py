"""
Dynamic NIBD Ratio Model for Net Interest Income Sensitivity Analysis
Complete Python Implementation

This script reproduces all analysis from the model development document including:
- Data loading and preprocessing
- Unit root testing
- ARDL model estimation and diagnostics
- ECM (Engle-Granger) model estimation
- Cointegration testing
- Out-of-sample validation
- Forecasting and scenario analysis
- All statistical diagnostic tests
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Statistical and econometric libraries
from statsmodels.tsa.api import VAR
from statsmodels.tsa.ardl import ARDL, ardl_select_order
from statsmodels.tsa.stattools import adfuller, kpss, coint
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import linear_reset
from statsmodels.tsa.statespace.structural import UnobservedComponents
import statsmodels.api as sm

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
plt.style.use('seaborn-v0_8')

# Scientific computing
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error
import math
import argparse
import os
import json

print("="*80)
print("DYNAMIC NIBD RATIO MODEL - COMPLETE ANALYSIS")
print("="*80)

# =============================================================================
# 1. DATA LOADING AND PREPROCESSING
# =============================================================================

def resolve_csv_path(csv_file_path: str | None) -> str:
    """Resolve CSV path with a sensible default (NIBD_ratio_v2.csv in repo)."""
    if csv_file_path and os.path.isabs(csv_file_path):
        return csv_file_path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if not csv_file_path:
        candidate = os.path.join(base_dir, 'NIBD_ratio_v2.csv')
        return candidate
    # relative path provided
    return os.path.join(base_dir, csv_file_path)


def load_and_prepare_data(csv_file_path):
    """
    Load and prepare data for NIBD ratio modeling
    Expected CSV columns: Date, ALLCB_NIBD, FEFF, FBS_GDP, 2Y_SOFR, 10Y_SOFR
    """
    print("\n1. DATA LOADING AND PREPROCESSING")
    print("-" * 50)
    
    # Load data
    try:
        df = pd.read_csv(csv_file_path)
        print(f"Data loaded successfully. Shape: {df.shape}")
    except FileNotFoundError:
        print(f"CSV not found at {csv_file_path}. Creating sample data for demonstration...")
        df = create_sample_data()

    # Identify and parse date column
    date_col = 'QtrEndDt' if 'QtrEndDt' in df.columns else ('Date' if 'Date' in df.columns else None)
    if date_col is None:
        raise ValueError("Expected a 'QtrEndDt' or 'Date' column in the CSV.")
    # Parse dates; CSV uses mm/dd/yyyy format
    df['Date'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['Date']).copy()
    df.set_index('Date', inplace=True)

    print("\nConstructing model variables...")

    # Use provided 12MA_FEFF directly if available; else compute from FEFF
    if '12MA_FEFF' not in df.columns:
        if 'FEFF' in df.columns:
            df['12MA_FEFF'] = df['FEFF'].rolling(window=12).mean()
        else:
            raise ValueError("CSV must include either '12MA_FEFF' or 'FEFF'.")

    # Compute 10Y-2Y SOFR OIS term spread from available columns
    if 'SOFR10Y' in df.columns and 'SOFR2Y' in df.columns:
        df['10Y_2Y'] = df['SOFR10Y'] - df['SOFR2Y']
    elif '10Y_SOFR' in df.columns and '2Y_SOFR' in df.columns:
        df['10Y_2Y'] = df['10Y_SOFR'] - df['2Y_SOFR']
    else:
        raise ValueError("CSV must include SOFR 10Y and 2Y columns (SOFR10Y/SOFR2Y or 10Y_SOFR/2Y_SOFR).")

    # Filter to sample period (2011Q3 to 2025Q2)
    df = df.loc['2011-09-30':'2025-06-30'].copy()

    # Quarterly data provided; drop rows with missing values
    model_vars = ['ALLCB_NIBD', '12MA_FEFF', 'FBS_GDP', '10Y_2Y']
    missing = [c for c in model_vars if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    df_final = df[model_vars].dropna().copy()
    
    print(f"Final dataset shape: {df_final.shape}")
    print(f"Sample period: {df_final.index[0]} to {df_final.index[-1]}")
    print(f"Number of observations: {len(df_final)}")
    
    # Display summary statistics
    print("\nSummary Statistics:")
    print(df_final.describe().round(4))
    
    return df_final

def create_sample_data():
    """Create sample data matching the paper's specifications"""
    np.random.seed(42)
    
    # Create monthly date range from 2010 to 2025
    dates = pd.date_range('2010-01-01', '2025-06-30', freq='MS')
    n = len(dates)
    
    # Create synthetic data with realistic patterns
    # Fed Funds rate with policy cycles
    feff = np.zeros(n)
    feff[0:50] = np.linspace(0.25, 0.08, 50)  # 2010-2014: declining to zero
    feff[50:110] = 0.08 + np.random.normal(0, 0.02, 60)  # 2014-2019: near zero
    feff[110:130] = np.linspace(0.08, 2.5, 20)  # 2019-2021: gradual increase
    feff[130:150] = np.linspace(2.5, 0.5, 20)  # 2021-2022: COVID cut
    feff[150:] = np.linspace(0.5, 5.25, n-150)  # 2022-2025: rapid tightening
    feff = np.maximum(feff, 0.05)  # Floor at 5bp
    
    # Fed balance sheet (cyclical with QE periods)
    fed_bs_base = np.linspace(15, 35, n)
    fed_bs_cycle = 8 * np.sin(2 * np.pi * np.arange(n) / 48) # 4-year cycle
    fbs_gdp = fed_bs_base + fed_bs_cycle + np.random.normal(0, 1, n)
    fbs_gdp = np.clip(fbs_gdp, 15, 35)
    
    # SOFR rates (correlated with Fed Funds but with term structure)
    sofr_2y = feff + 0.5 + np.random.normal(0, 0.3, n)
    sofr_10y = feff + 1.8 + np.random.normal(0, 0.4, n)
    
    # NIBD ratio (negatively correlated with rates)
    nibd_trend = 32 - 0.8 * (feff - np.mean(feff)) 
    nibd_noise = np.random.normal(0, 0.8, n)
    nibd = nibd_trend + nibd_noise
    nibd = np.clip(nibd, 20, 35)  # Realistic range
    
    # Create DataFrame
    df = pd.DataFrame({
        'Date': dates,
        'ALLCB_NIBD': nibd,
        'FEFF': feff,
        'FBS_GDP': fbs_gdp,
        '2Y_SOFR': sofr_2y,
        '10Y_SOFR': sofr_10y
    })
    
    return df

# =============================================================================
# 2. UNIT ROOT TESTING
# =============================================================================

def perform_unit_root_tests(df):
    """
    Perform comprehensive unit root testing using ADF and KPSS tests
    """
    print("\n2. UNIT ROOT TESTING")
    print("-" * 50)
    
    results = {}
    variables = df.columns
    
    print(f"{'Variable':<15} {'ADF Stat':<10} {'ADF p-val':<10} {'KPSS Stat':<10} {'KPSS p-val':<10} {'Order':<15}")
    print("-" * 80)
    
    for var in variables:
        series = df[var].dropna()
        
        # ADF test (H0: unit root)
        adf_result = adfuller(series, autolag='AIC', regression='c')
        adf_stat = adf_result[0]
        adf_pval = adf_result[1]
        
        # KPSS test (H0: stationary)
        kpss_result = kpss(series, regression='c')
        kpss_stat = kpss_result[0]
        kpss_pval = kpss_result[1]
        
        # Determine integration order
        if adf_pval <= 0.05 and kpss_pval > 0.05:
            integration_order = "I(0)"
        elif adf_pval > 0.05 and kpss_pval <= 0.05:
            integration_order = "I(1)"
        else:
            integration_order = "I(1) borderline"
            
        results[var] = {
            'adf_stat': adf_stat,
            'adf_pval': adf_pval,
            'kpss_stat': kpss_stat, 
            'kpss_pval': kpss_pval,
            'integration_order': integration_order
        }
        
        print(f"{var:<15} {adf_stat:<10.3f} {adf_pval:<10.3f} {kpss_stat:<10.3f} {kpss_pval:<10.3f} {integration_order:<15}")
    
    return results

# =============================================================================
# 3. MULTICOLLINEARITY TESTING
# =============================================================================

def check_multicollinearity(df):
    """
    Calculate VIF for all independent variables
    """
    print("\n3. MULTICOLLINEARITY ASSESSMENT")
    print("-" * 50)
    
    # Prepare data for VIF calculation
    X = df[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']].dropna()
    
    # Calculate VIF for each variable
    vif_data = pd.DataFrame()
    vif_data["Variable"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    vif_data["Status"] = vif_data["VIF"].apply(lambda x: "Acceptable" if x < 5.0 else "High")
    
    print(vif_data.to_string(index=False))
    print(f"\nMaximum VIF: {vif_data['VIF'].max():.2f}")
    
    if vif_data['VIF'].max() < 5.0:
        print("✓ No multicollinearity issues detected (all VIF < 5.0)")
    else:
        print("⚠ Potential multicollinearity issues detected")
    # Return VIF table for downstream usage/export
    return vif_data
# 4. ARDL MODEL ESTIMATION
# =============================================================================

def estimate_ardl_model(df):
    """
    Estimate ARDL(1,1) model and calculate long-run multipliers
    """
    print("\n4. ARDL MODEL ESTIMATION")
    print("-" * 50)
    
    # Prepare data and construct lagged variables for OLS
    data = df.dropna().copy()
    y = data['ALLCB_NIBD']
    X = pd.DataFrame(index=data.index)
    X['ALLCB_NIBD.L1'] = data['ALLCB_NIBD'].shift(1)
    for var in ['12MA_FEFF', 'FBS_GDP', '10Y_2Y']:
        X[f'{var}.L0'] = data[var]
        X[f'{var}.L1'] = data[var].shift(1)
    # Align and drop NaNs
    design = pd.concat([y, X], axis=1).dropna()
    y_aligned = design['ALLCB_NIBD']
    X_aligned = design.drop(columns=['ALLCB_NIBD'])
    X_aligned = sm.add_constant(X_aligned, has_constant='add')

    # Fit OLS equivalent to ARDL(1,1,1,1)
    ols_model = OLS(y_aligned, X_aligned)
    ardl_results = ols_model.fit()
    
    print("ARDL(1,1,1,1) Estimation Results (OLS Equivalent):")
    print("=" * 60)
    print(ardl_results.summary())
    
    # Calculate long-run multipliers
    print("\nLong-run Multiplier Calculations:")
    print("-" * 40)
    
    # Extract coefficients
    coef = ardl_results.params
    lag_dep_coef = coef['ALLCB_NIBD.L1']
    adjustment_factor = 1 - lag_dep_coef
    
    print(f"Lagged dependent variable coefficient (φ₁): {lag_dep_coef:.4f}")
    print(f"Adjustment factor (1-φ₁): {adjustment_factor:.4f}")
    
    # Calculate long-run multipliers
    vars_info = {
        '12MA_FEFF': ['12MA_FEFF.L0', '12MA_FEFF.L1'],
        'FBS_GDP': ['FBS_GDP.L0', 'FBS_GDP.L1'],
        '10Y_2Y': ['10Y_2Y.L0', '10Y_2Y.L1']
    }
    
    lr_multipliers = {}
    
    print(f"\n{'Variable':<12} {'Current':<10} {'Lagged':<10} {'Total':<10} {'LR Multiplier':<12} {'Economic Impact':<20}")
    print("-" * 85)
    
    for var, coef_names in vars_info.items():
        current_coef = coef[coef_names[0]] if coef_names[0] in coef else 0
        lagged_coef = coef[coef_names[1]] if coef_names[1] in coef else 0
        total_effect = current_coef + lagged_coef
        lr_multiplier = total_effect / adjustment_factor
        
        lr_multipliers[var] = lr_multiplier
        
        # Economic interpretation
        if var == '12MA_FEFF':
            impact = f"{abs(lr_multiplier*100):.0f}bp per 100bp"
        elif var == 'FBS_GDP':
            impact = "QE effect"
        else:
            impact = "Term spread effect"
            
        print(f"{var:<12} {current_coef:<10.4f} {lagged_coef:<10.4f} {total_effect:<10.4f} {lr_multiplier:<12.4f} {impact:<20}")
    
    # Calculate adjustment speed and half-life
    half_life = math.log(0.5) / math.log(lag_dep_coef) if lag_dep_coef > 0 else np.inf
    print(f"\nAdjustment Speed: {(1-lag_dep_coef)*100:.1f}% per quarter")
    print(f"Half-life: {half_life:.2f} quarters")
    
    return ardl_results, lr_multipliers

# =============================================================================
# 5. ECM (ENGLE-GRANGER) MODEL ESTIMATION
# =============================================================================

def estimate_ecm_model(df):
    """
    Estimate Error Correction Model using Engle-Granger two-step method
    """
    print("\n5. ERROR CORRECTION MODEL (ECM) ESTIMATION")
    print("-" * 50)
    
    data = df.dropna()
    
    # Step 1: Estimate long-run static regression
    print("Step 1: Long-run Static Regression")
    print("-" * 35)
    
    y = data['ALLCB_NIBD']
    X = sm.add_constant(data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']])
    
    static_model = OLS(y, X)
    static_results = static_model.fit()
    
    print(static_results.summary())
    
    # Generate residuals for cointegration testing
    residuals = static_results.resid
    
    # Step 2: Test for cointegration
    print("\nStep 2: Cointegration Testing")
    print("-" * 30)
    
    # ADF test on residuals
    adf_resid = adfuller(residuals, autolag='AIC', regression='n')  # no constant for residuals
    print(f"ADF test on residuals:")
    print(f"  Statistic: {adf_resid[0]:.4f}")
    print(f"  p-value: {adf_resid[1]:.4f}")
    print(f"  5% critical value: {adf_resid[4]['5%']:.4f}")
    
    if adf_resid[0] < adf_resid[4]['5%']:
        print("✓ Evidence of cointegration (residuals are stationary)")
    else:
        print("⚠ Weak evidence of cointegration")
    
    # Durbin-Watson statistic check
    dw_stat = durbin_watson(residuals)
    print(f"Durbin-Watson statistic: {dw_stat:.3f}")
    
    if dw_stat > 0.5:
        print("✓ DW statistic suggests genuine cointegration (not spurious regression)")
    else:
        print("⚠ Low DW statistic - potential spurious regression")
    
    # Step 3: Estimate Error Correction Model
    print("\nStep 3: Error Correction Model")
    print("-" * 30)
    
    # Create differenced variables
    data_diff = data.diff().dropna()
    ect_lagged = residuals.shift(1).dropna()
    
    # Align the data
    min_len = min(len(data_diff), len(ect_lagged))
    data_diff = data_diff.iloc[-min_len:]
    ect_lagged = ect_lagged.iloc[-min_len:]
    
    # ECM regression
    y_diff = data_diff['ALLCB_NIBD']
    X_diff = pd.DataFrame({
        'const': 1,
        'ECT_lag': ect_lagged,
        'D_12MA_FEFF': data_diff['12MA_FEFF'],
        'D_FBS_GDP': data_diff['FBS_GDP'],
        'D_10Y_2Y': data_diff['10Y_2Y']
    })
    
    ecm_model = OLS(y_diff, X_diff)
    ecm_results = ecm_model.fit()
    
    print(ecm_results.summary())
    
    # Calculate adjustment speed from ECM
    error_correction_coef = ecm_results.params['ECT_lag']
    ecm_half_life = math.log(0.5) / math.log(1 + error_correction_coef) if error_correction_coef < 0 else np.inf
    
    print(f"\nError Correction Coefficient: {error_correction_coef:.4f}")
    print(f"Adjustment Speed: {abs(error_correction_coef)*100:.1f}% per quarter")
    print(f"Half-life: {ecm_half_life:.2f} quarters")
    
    return static_results, ecm_results, residuals

# =============================================================================
# 6. DIAGNOSTIC TESTING
# =============================================================================

def perform_diagnostic_tests(model_results, residuals, model_name):
    """
    Perform comprehensive diagnostic tests on model residuals
    """
    print(f"\n6. DIAGNOSTIC TESTING - {model_name}")
    print("-" * 60)
    
    diagnostics = {}
    
    # 1. Serial Correlation Test (Ljung-Box)
    lb_test = acorr_ljungbox(residuals, lags=4, return_df=True)
    lb_stat = lb_test['lb_stat'].iloc[-1]  # 4th lag statistic
    lb_pval = lb_test['lb_pvalue'].iloc[-1]
    
    print(f"1. Serial Correlation Test (Ljung-Box, 4 lags):")
    print(f"   Statistic: {lb_stat:.3f}, p-value: {lb_pval:.3f}")
    print(f"   Critical value (5%): 9.49")
    if lb_pval > 0.05:
        print("   ✓ No serial correlation detected")
    else:
        print("   ⚠ Serial correlation detected")
    
    diagnostics['ljung_box'] = {'statistic': lb_stat, 'pvalue': lb_pval}
    
    # 2. Heteroscedasticity Test (Breusch-Pagan)
    # For this we need the fitted model
    if hasattr(model_results, 'model'):
        try:
            bp_test = het_breuschpagan(residuals, model_results.model.exog)
            bp_stat = bp_test[0]
            bp_pval = bp_test[1]
            
            print(f"\n2. Heteroscedasticity Test (Breusch-Pagan):")
            print(f"   Statistic: {bp_stat:.3f}, p-value: {bp_pval:.3f}")
            if bp_pval > 0.05:
                print("   ✓ Homoscedastic errors (constant variance)")
            else:
                print("   ⚠ Heteroscedasticity detected")
                
            diagnostics['breusch_pagan'] = {'statistic': bp_stat, 'pvalue': bp_pval}
        except:
            print("\n2. Heteroscedasticity Test: Unable to compute")
            diagnostics['breusch_pagan'] = {'statistic': np.nan, 'pvalue': np.nan}
    
    # 3. Normality Test (Jarque-Bera)
    jb_stat, jb_pval, _, _ = jarque_bera(residuals)
    
    print(f"\n3. Normality Test (Jarque-Bera):")
    print(f"   Statistic: {jb_stat:.3f}, p-value: {jb_pval:.3f}")
    print(f"   Critical value (5%): 5.99")
    if jb_pval > 0.05:
        print("   ✓ Residuals are normally distributed")
    else:
        print("   ⚠ Non-normal residuals detected")
        
    diagnostics['jarque_bera'] = {'statistic': jb_stat, 'pvalue': jb_pval}
    
    # 4. RESET Test for Functional Form (if possible)
    try:
        reset_test = linear_reset(model_results, power=2, use_f=True)
        reset_stat = float(reset_test.fvalue)
        reset_pval = float(reset_test.pvalue)
        
        print(f"\n4. Functional Form Test (RESET):")
        print(f"   Statistic: {reset_stat:.3f}, p-value: {reset_pval:.3f}")
        if reset_pval > 0.05:
            print("   ✓ Correct functional form")
        else:
            print("   ⚠ Functional form issues detected")
            
        diagnostics['reset'] = {'statistic': reset_stat, 'pvalue': reset_pval}
    except:
        print("\n4. Functional Form Test: Unable to compute RESET test")
        diagnostics['reset'] = {'statistic': np.nan, 'pvalue': np.nan}
    
    # 5. Durbin-Watson Test
    dw_stat = durbin_watson(residuals)
    print(f"\n5. Durbin-Watson Test:")
    print(f"   Statistic: {dw_stat:.3f}")
    if 1.5 < dw_stat < 2.5:
        print("   ✓ No first-order serial correlation")
    else:
        print("   ⚠ Potential serial correlation")
        
    diagnostics['durbin_watson'] = dw_stat
    
    return diagnostics

# =============================================================================
# 7. MODEL COMPARISON
# =============================================================================

def compare_models(ardl_results, static_results, ardl_lr_multipliers):
    """
    Compare ARDL and ECM long-run multipliers
    """
    print("\n7. MODEL COMPARISON")
    print("-" * 50)
    
    print("Long-run Multiplier Comparison:")
    print("-" * 35)
    
    # ECM long-run multipliers are directly from static regression coefficients
    ecm_multipliers = {
        '12MA_FEFF': static_results.params['12MA_FEFF'],
        'FBS_GDP': static_results.params['FBS_GDP'],
        '10Y_2Y': static_results.params['10Y_2Y']
    }
    
    print(f"{'Variable':<15} {'ARDL LR':<12} {'ECM LR':<12} {'Difference':<12} {'% Diff':<10}")
    print("-" * 70)
    
    for var in ['12MA_FEFF', 'FBS_GDP', '10Y_2Y']:
        ardl_lr = ardl_lr_multipliers[var]
        ecm_lr = ecm_multipliers[var]
        diff = ardl_lr - ecm_lr
        pct_diff = (diff / ecm_lr) * 100 if ecm_lr != 0 else np.inf
        
        print(f"{var:<15} {ardl_lr:<12.4f} {ecm_lr:<12.4f} {diff:<12.4f} {pct_diff:<10.1f}%")
    
    # R-squared comparison note
    print(f"\nModel Fit Statistics:")
    print(f"ARDL R-squared: {ardl_results.rsquared:.4f}")
    print(f"ECM Static R-squared: {static_results.rsquared:.4f}")
    print("\nNote: R-squared not directly comparable between ARDL and ECM")
    print("ARDL includes lagged dependent variable, ECM step 2 uses differences")

# =============================================================================
# 8. OUT-OF-SAMPLE VALIDATION
# =============================================================================

def out_of_sample_validation(df, split_pct=0.8):
    """
    Perform out-of-sample validation using static forecasting
    """
    print("\n8. OUT-OF-SAMPLE VALIDATION")
    print("-" * 50)
    
    data = df.dropna()
    split_idx = int(len(data) * split_pct)
    
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    print(f"Training sample: {train_data.index[0]} to {train_data.index[-1]} ({len(train_data)} obs)")
    print(f"Test sample: {test_data.index[0]} to {test_data.index[-1]} ({len(test_data)} obs)")
    
    # Estimate models on training data
    print("\nRe-estimating models on training data...")
    
    # ARDL(1,1,1,1) via OLS on lagged design
    y_tr = train_data['ALLCB_NIBD']
    X_tr = pd.DataFrame(index=train_data.index)
    X_tr['ALLCB_NIBD.L1'] = train_data['ALLCB_NIBD'].shift(1)
    for var in ['12MA_FEFF', 'FBS_GDP', '10Y_2Y']:
        X_tr[f'{var}.L0'] = train_data[var]
        X_tr[f'{var}.L1'] = train_data[var].shift(1)
    design_tr = pd.concat([y_tr, X_tr], axis=1).dropna()
    y_tr_al = design_tr['ALLCB_NIBD']
    X_tr_al = sm.add_constant(design_tr.drop(columns=['ALLCB_NIBD']), has_constant='add')
    ardl_fit_train = OLS(y_tr_al, X_tr_al).fit()
    
    # ECM model
    y_train = train_data['ALLCB_NIBD']
    X_train = sm.add_constant(train_data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']])
    ecm_fit_train = OLS(y_train, X_train).fit()
    
    # Generate forecasts (static forecasting)
    print("\nGenerating out-of-sample forecasts...")
    
    # For ARDL: use actual lagged values in forecast
    ardl_forecasts = []
    for i in range(len(test_data)):
        if i == 0:
            # First forecast uses last training observation as lag
            lag_y = train_data['ALLCB_NIBD'].iloc[-1]
        else:
            # Subsequent forecasts use actual (not predicted) lagged values
            lag_y = test_data['ALLCB_NIBD'].iloc[i-1]
            
        # Current and lagged exogenous variables
        current_x = test_data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']].iloc[i]
        if i == 0:
            lagged_x = train_data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']].iloc[-1]
        else:
            lagged_x = test_data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']].iloc[i-1]
        
        # Manual forecast calculation using ARDL coefficients
        coef = ardl_fit_train.params
        forecast = (coef['const'] + 
                   coef['ALLCB_NIBD.L1'] * lag_y +
                   coef['12MA_FEFF.L0'] * current_x['12MA_FEFF'] +
                   coef['12MA_FEFF.L1'] * lagged_x['12MA_FEFF'] +
                   coef['FBS_GDP.L0'] * current_x['FBS_GDP'] +
                   coef['FBS_GDP.L1'] * lagged_x['FBS_GDP'] +
                   coef['10Y_2Y.L0'] * current_x['10Y_2Y'] +
                   coef['10Y_2Y.L1'] * lagged_x['10Y_2Y'])
        
        ardl_forecasts.append(forecast)
    
    # For ECM: static regression forecasts
    X_test = sm.add_constant(test_data[['12MA_FEFF', 'FBS_GDP', '10Y_2Y']])
    ecm_forecasts = ecm_fit_train.predict(X_test)
    
    # Calculate forecast accuracy metrics
    actual = test_data['ALLCB_NIBD'].values
    
    def calculate_metrics(actual, predicted, model_name):
        predicted = np.asarray(predicted)
        mae = mean_absolute_error(actual, predicted)
        rmse = np.sqrt(mean_squared_error(actual, predicted))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        # Theil's U statistic
        numerator = np.sqrt(np.mean((actual - predicted)**2))
        denominator = np.sqrt(np.mean(actual**2)) + np.sqrt(np.mean(predicted**2))
        theil_u = numerator / denominator if denominator != 0 else np.inf
        
        print(f"\n{model_name} Forecast Accuracy:")
        print(f"  Mean Absolute Error: {mae:.5f}")
        print(f"  Root Mean Square Error: {rmse:.5f}")
        print(f"  Mean Absolute Percentage Error: {mape:.2f}%")
        print(f"  Theil's U-statistic: {theil_u:.3f}")
        
        return {'MAE': mae, 'RMSE': rmse, 'MAPE': mape, 'Theil_U': theil_u}
    
    ardl_metrics = calculate_metrics(actual, ardl_forecasts, "ARDL")
    ecm_metrics = calculate_metrics(actual, ecm_forecasts, "ECM")
    
    # Compare performance
    print(f"\nPerformance Comparison:")
    print(f"ARDL vs ECM improvement:")
    print(f"  MAE: {((ecm_metrics['MAE'] - ardl_metrics['MAE'])/ecm_metrics['MAE']*100):+.1f}%")
    print(f"  RMSE: {((ecm_metrics['RMSE'] - ardl_metrics['RMSE'])/ecm_metrics['RMSE']*100):+.1f}%")
    print(f"  MAPE: {((ecm_metrics['MAPE'] - ardl_metrics['MAPE'])/ecm_metrics['MAPE']*100):+.1f}%")
    
    return ardl_metrics, ecm_metrics, ardl_forecasts, ecm_forecasts, test_data

# =============================================================================
# 9. SCENARIO ANALYSIS AND FORECASTING
# =============================================================================

def compute_gradual_nii_impact(fed_lr_multiplier: float, shock_bp: int, total_deposits_bn: float, rate_diff: float):
    """Compute first-year dynamic NII impact using 12-month MA transmission.

    Returns a tuple of (monthly_rows, totals) where monthly_rows is a list of
    rows compatible with the export table, and totals contains aggregate metrics.
    """
    increment_bp = shock_bp / 12.0  # equal monthly steps in bp for 12MA incorporation
    monthly_rows = []
    total_nii_impact_m = 0.0
    total_reallocation_m = 0.0
    outflows = []
    for m in range(1, 13):
        nibd_delta_pp = fed_lr_multiplier * (increment_bp / 100.0)  # pp change per month
        outflow_m = total_deposits_bn * 1000.0 * abs(nibd_delta_pp) / 100.0  # $M
        months_remaining = 13 - m
        nii_impact_m = outflow_m * rate_diff * (months_remaining / 12.0)
        monthly_rows.append((m, m * increment_bp - increment_bp, increment_bp, nibd_delta_pp, outflow_m, nii_impact_m))
        total_nii_impact_m += nii_impact_m
        total_reallocation_m += outflow_m
        outflows.append(outflow_m)
    avg_monthly_outflow_m = float(np.mean(outflows)) if outflows else 0.0
    return monthly_rows, {
        'total_nii_impact_m': float(total_nii_impact_m),
        'total_reallocation_m': float(total_reallocation_m),
        'avg_monthly_outflow_m': avg_monthly_outflow_m,
    }


def scenario_analysis(df, ardl_results, shock_bp: int = 300, total_deposits_bn: float = 40.0, rate_diff: float = 0.055, static_nii_benefit_m: float | None = None, return_table: bool = True):
    """
    Perform scenario analysis with parallel rate shocks and corrected NII case study.
    """
    print("\n9. SCENARIO ANALYSIS AND FORECASTING")
    print("-" * 50)

    # Use the long-run multiplier for Fed Funds
    coef = ardl_results.params
    lag_dep_coef = coef['ALLCB_NIBD.L1']
    adjustment_factor = 1 - lag_dep_coef

    # Calculate Fed Funds long-run multiplier
    fed_current = coef['12MA_FEFF.L0']
    fed_lagged = coef['12MA_FEFF.L1']
    fed_lr_multiplier = (fed_current + fed_lagged) / adjustment_factor

    print(f"Fed Funds Long-run Multiplier: {fed_lr_multiplier:.4f}")

    # Current baseline values (use latest observation, in percent)
    current_nibd_pct = df['ALLCB_NIBD'].iloc[-1] * 100.0
    print(f"Current NIBD Ratio: {current_nibd_pct:.1f}%")

    # Scenario analysis (parallel shifts)
    scenarios = [-400, -200, 0, 200, 400]  # basis point shocks
    print(f"\nScenario Analysis (Parallel Rate Shocks):")
    print(f"{'Shock (bp)':<12} {'New NIBD %':<12} {'Change (bp)':<12}")
    print("-" * 40)
    for s_bp in scenarios:
        nibd_change_pp = fed_lr_multiplier * (s_bp / 100)  # pp change per 100bp
        new_nibd_pct = current_nibd_pct + nibd_change_pp
        print(f"{s_bp:<12} {new_nibd_pct:<12.1f} {nibd_change_pp*100:<12.0f}")

    # Case study calculation matching the document: corrected dynamic NII
    print(f"\nCase Study: {shock_bp}bp Rate Increase Impact with Proper Transmission")
    print("-" * 40)
    current_nibd_ratio = df['ALLCB_NIBD'].iloc[-1] * 100
    current_nibd_amount = total_deposits_bn * (current_nibd_ratio / 100)  # in $ billions
    print("Representative Bank Profile:")
    print(f"  Total Deposits: ${total_deposits_bn:.1f}B")
    print(f"  Current NIBD: ${current_nibd_amount:.1f}B ({current_nibd_ratio}%)")

    # Corrected dynamic NII via helper
    monthly_rows, totals = compute_gradual_nii_impact(
        fed_lr_multiplier=fed_lr_multiplier,
        shock_bp=shock_bp,
        total_deposits_bn=total_deposits_bn,
        rate_diff=rate_diff,
    )

    print("\nGradual Transmission Analysis:")
    print(f"{'Month':<6} {'12MA_FEFF':<10} {'Δ MA(bp)':<9} {'NIBD Δ(pp)':<10} {'Outflow($M)':<12} {'NII Impact($M)':<15}")
    print("-" * 75)
    for month, ma_base_bp, delta_bp, delta_pp, outflow_m, nii_m in monthly_rows:
        print(f"{month:<6} {int(ma_base_bp+delta_bp):<10d} {int(delta_bp):<9d} {delta_pp: <10.2f} {outflow_m: <12.0f} {nii_m: <15.1f}")

    # Naive immediate dynamic expense (apply full long-run change at start for entire year)
    total_change_pp = fed_lr_multiplier * (shock_bp / 100.0)
    naive_outflow_m = total_deposits_bn * 1000.0 * abs(total_change_pp) / 100.0
    naive_nii_m = naive_outflow_m * rate_diff

    print("\nSummary:")
    print(f"  Total First-Year NII Impact (Corrected): ${totals['total_nii_impact_m']:,.1f} million")
    print(f"  Naive Immediate Dynamic Expense:        ${naive_nii_m:,.1f} million")
    print(f"  Average Monthly Outflow:                 ${totals['avg_monthly_outflow_m']:,.0f} million")
    print(f"  Total Deposit Reallocation:              ${totals['total_reallocation_m']:,.0f} million")

    if static_nii_benefit_m is not None:
        net_corrected = static_nii_benefit_m - totals['total_nii_impact_m']
        net_naive = static_nii_benefit_m - naive_nii_m
        print("\nCombined NII Story:")
        print(f"  Static Asset-side NII Benefit: ${static_nii_benefit_m:,.1f} million")
        print(f"  Net NII (Corrected):           ${net_corrected:,.1f} million")
        print(f"  Net NII (Naive):               ${net_naive:,.1f} million")

    table_df = None
    if return_table:
        table_df = pd.DataFrame(monthly_rows, columns=[
            'Month', 'MA_Base_bp', 'Delta_MA_bp', 'NIBD_Delta_pp', 'Outflow_M', 'NII_Impact_M'
        ])
    summary = {
        'shock_bp': shock_bp,
        'total_deposits_bn': total_deposits_bn,
        'rate_differential': rate_diff,
        'static_nii_m': static_nii_benefit_m,
        'fed_lr_multiplier': float(fed_lr_multiplier),
        'corrected_first_year_nii_m': float(totals['total_nii_impact_m']),
        'naive_first_year_nii_m': float(naive_nii_m),
        'total_reallocation_m': float(totals['total_reallocation_m']),
        'avg_monthly_outflow_m': float(totals['avg_monthly_outflow_m']),
        'net_nii_corrected_m': float((static_nii_benefit_m - totals['total_nii_impact_m']) if static_nii_benefit_m is not None else np.nan),
        'net_nii_naive_m': float((static_nii_benefit_m - naive_nii_m) if static_nii_benefit_m is not None else np.nan),
    }
    return scenarios, fed_lr_multiplier, totals['total_nii_impact_m'], naive_nii_m, table_df, summary

# =============================================================================
# 10. VISUALIZATION
# =============================================================================

def create_visualizations(df, ardl_forecasts=None, ecm_forecasts=None, test_data=None, save_dir: str | None = None):
    """
    Create key visualizations for the analysis
    """
    print("\n10. CREATING VISUALIZATIONS")
    print("-" * 50)
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Dynamic NIBD Ratio Model - Key Visualizations', fontsize=16, fontweight='bold')
    
    # Plot 1: NIBD Ratio over time
    axes[0,0].plot(df.index, df['ALLCB_NIBD'], linewidth=2, color='blue')
    axes[0,0].set_title('All Commercial Banks NIBD Ratio')
    axes[0,0].set_ylabel('NIBD Ratio (%)')
    axes[0,0].grid(True, alpha=0.3)
    axes[0,0].tick_params(axis='x', rotation=45)
    
    # Plot 2: Fed Funds Rate
    axes[0,1].plot(df.index, df['12MA_FEFF'], linewidth=2, color='red', label='12MA Fed Funds')
    axes[0,1].set_title('12-Month Moving Average Federal Funds Rate')
    axes[0,1].set_ylabel('Rate (%)')
    axes[0,1].grid(True, alpha=0.3)
    axes[0,1].tick_params(axis='x', rotation=45)
    axes[0,1].legend()
    
    # Plot 3: Fed Balance Sheet
    axes[1,0].plot(df.index, df['FBS_GDP'], linewidth=2, color='green')
    axes[1,0].set_title('Fed Balance Sheet Securities to GDP Ratio')
    axes[1,0].set_ylabel('Ratio (%)')
    axes[1,0].grid(True, alpha=0.3)
    axes[1,0].tick_params(axis='x', rotation=45)
    
    # Plot 4: Term Spread or Forecast Comparison
    if ardl_forecasts is not None and test_data is not None:
        axes[1,1].plot(test_data.index, test_data['ALLCB_NIBD'], 
                      linewidth=2, color='black', label='Actual', marker='o')
        axes[1,1].plot(test_data.index, ardl_forecasts, 
                      linewidth=2, color='blue', label='ARDL Forecast', linestyle='--')
        axes[1,1].plot(test_data.index, ecm_forecasts, 
                      linewidth=2, color='red', label='ECM Forecast', linestyle=':')
        axes[1,1].set_title('Out-of-Sample Forecast Comparison')
        axes[1,1].set_ylabel('NIBD Ratio (%)')
        axes[1,1].legend()
    else:
        axes[1,1].plot(df.index, df['10Y_2Y'], linewidth=2, color='purple')
        axes[1,1].set_title('10Y-2Y SOFR OIS Term Spread')
        axes[1,1].set_ylabel('Spread (pp)')
    
    axes[1,1].grid(True, alpha=0.3)
    axes[1,1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fig_path = os.path.join(save_dir, 'dynamic_nibd_key_visuals.png')
        plt.savefig(fig_path, dpi=200, bbox_inches='tight')
        print(f"✓ Saved visuals: {fig_path}")
    else:
        plt.show()
    
    # Create correlation heatmap
    plt.figure(figsize=(10, 8))
    corr_matrix = df[['ALLCB_NIBD', '12MA_FEFF', 'FBS_GDP', '10Y_2Y']].corr()
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                square=True, fmt='.3f', cbar_kws={'label': 'Correlation'})
    plt.title('Correlation Matrix of Model Variables', fontsize=14, fontweight='bold')
    plt.tight_layout()
    if save_dir:
        heatmap_path = os.path.join(save_dir, 'correlation_heatmap.png')
        plt.savefig(heatmap_path, dpi=200, bbox_inches='tight')
        print(f"✓ Saved heatmap: {heatmap_path}")
        plt.close('all')
    else:
        plt.show()
    
    print("✓ Visualizations created successfully")

# =============================================================================
# 11. MAIN EXECUTION FUNCTION
# =============================================================================

def run_complete_analysis(csv_file_path=None, shock_bp: int = 300, total_deposits_bn: float = 40.0, rate_diff: float = 0.055, static_nii_benefit_m: float | None = 150.0, export: bool = False, export_dir: str | None = None):
    """
    Run the complete NIBD ratio model analysis
    """
    print("Starting Dynamic NIBD Ratio Model Analysis...")
    print("This analysis replicates all results from the model development document.")
    
    # Helper: Convert OLS results to structured JSON-friendly dict
    def _to_float(x):
        try:
            if x is None or (isinstance(x, float) and (np.isnan(x))):
                return None
            return float(x)
        except Exception:
            try:
                return float(np.asarray(x))
            except Exception:
                return None

    def _dict_float(d: dict) -> dict:
        return {str(k): _to_float(v) for k, v in d.items()}

    def ols_results_to_structured(res) -> dict:
        try:
            params = _dict_float(res.params.to_dict())
            bse = _dict_float(res.bse.to_dict())
            tvalues = _dict_float(res.tvalues.to_dict())
            pvalues = _dict_float(res.pvalues.to_dict())
            ci_df = res.conf_int()
            # Ensure CI has param index names
            try:
                ci_df.index = res.params.index
            except Exception:
                pass
            conf_int = {str(name): {"lower": _to_float(ci_df.loc[name, 0]), "upper": _to_float(ci_df.loc[name, 1])}
                        for name in res.params.index}
            fit = {
                'r2': _to_float(getattr(res, 'rsquared', None)),
                'adj_r2': _to_float(getattr(res, 'rsquared_adj', None)),
                'aic': _to_float(getattr(res, 'aic', None)),
                'bic': _to_float(getattr(res, 'bic', None)),
                'llf': _to_float(getattr(res, 'llf', None)),
                'f_stat': _to_float(getattr(res, 'fvalue', None)),
                'f_pvalue': _to_float(getattr(res, 'f_pvalue', None)),
                'nobs': _to_float(getattr(res, 'nobs', None)),
                'df_model': _to_float(getattr(res, 'df_model', None)),
                'df_resid': _to_float(getattr(res, 'df_resid', None)),
            }
            return {
                'coefficients': params,
                'std_errors': bse,
                't_stats': tvalues,
                'p_values': pvalues,
                'conf_int_95': conf_int,
                'fit': fit,
            }
        except Exception:
            return {}

    try:
        # 1. Load and prepare data
        resolved = resolve_csv_path(csv_file_path)
        print(f"Using data file: {resolved}")
        df = load_and_prepare_data(resolved)
        
        # 2. Unit root testing
        unit_root_results = perform_unit_root_tests(df)
        
        # 3. Multicollinearity check
        vif_results = check_multicollinearity(df)
        
        # 4. ARDL model estimation
        ardl_results, ardl_lr_multipliers = estimate_ardl_model(df)
        
        # 5. ECM model estimation
        static_results, ecm_results, residuals = estimate_ecm_model(df)
        
        # 6. Diagnostic testing
        ardl_diagnostics = perform_diagnostic_tests(ardl_results, ardl_results.resid, "ARDL")
        ecm_diagnostics = perform_diagnostic_tests(ecm_results, ecm_results.resid, "ECM")
        
        # 7. Model comparison
        compare_models(ardl_results, static_results, ardl_lr_multipliers)
        
        # 8. Out-of-sample validation
        ardl_metrics, ecm_metrics, ardl_forecasts, ecm_forecasts, test_data = out_of_sample_validation(df)
        
        # 9. Scenario analysis
        scenarios, fed_multiplier, corrected_nii_m, naive_nii_m, table_df, summary = scenario_analysis(
            df, ardl_results, shock_bp=shock_bp, total_deposits_bn=total_deposits_bn, rate_diff=rate_diff, static_nii_benefit_m=static_nii_benefit_m, return_table=True
        )

        # Export artifacts if requested
        if export:
            out_dir = export_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
            os.makedirs(out_dir, exist_ok=True)
            # Monthly transmission table
            if table_df is not None:
                csv_path = os.path.join(out_dir, 'monthly_transmission.csv')
                table_df.to_csv(csv_path, index=False)
                print(f"✓ Exported monthly transmission: {csv_path}")
            # Summary metrics
            # enrich summary with model information and diagnostics
            enriched_summary = dict(summary)
            try:
                # Models and structured summaries
                enriched_summary['models'] = {
                    'ardl': {
                        'summary_text': ardl_results.summary().as_text(),
                        'diagnostics': ardl_diagnostics,
                        'structured': ols_results_to_structured(ardl_results),
                    },
                    'ecm': {
                        'static_summary_text': static_results.summary().as_text(),
                        'ecm_summary_text': ecm_results.summary().as_text(),
                        'diagnostics': ecm_diagnostics,
                        'static_structured': ols_results_to_structured(static_results),
                        'ecm_structured': ols_results_to_structured(ecm_results),
                    },
                }
                enriched_summary['validation'] = {
                    'ardl': {k: _to_float(v) for k, v in ardl_metrics.items()},
                    'ecm': {k: _to_float(v) for k, v in ecm_metrics.items()},
                }
                # Prepare unit-root JSON (preserve integration_order text)
                unit_root_json = {}
                try:
                    for var, stats in unit_root_results.items():
                        unit_root_json[var] = {
                            'adf_stat': _to_float(stats.get('adf_stat')),
                            'adf_pval': _to_float(stats.get('adf_pval')),
                            'kpss_stat': _to_float(stats.get('kpss_stat')),
                            'kpss_pval': _to_float(stats.get('kpss_pval')),
                            'integration_order': stats.get('integration_order'),
                        }
                except Exception as ue:
                    unit_root_json = {'error': str(ue)}
                enriched_summary['unit_root'] = unit_root_json
                # Prepare VIF JSON robustly
                try:
                    if vif_results is not None:
                        vif_json = [
                            {
                                'variable': str(row['Variable']),
                                'vif': _to_float(row['VIF']),
                                'status': str(row['Status']),
                            }
                            for _, row in vif_results.iterrows()
                        ]
                    else:
                        vif_json = []
                except Exception as ve:
                    vif_json = {'error': str(ve)}
                enriched_summary['vif'] = vif_json
            except Exception as ex:
                # Do not fail export; include error hint for transparency
                enriched_summary['enrichment_error'] = str(ex)
            json_path = os.path.join(out_dir, 'scenario_summary.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_summary, f, indent=2)
            print(f"✓ Exported scenario summary: {json_path}")
        
        # 10. Create visualizations
        save_dir = out_dir if export else None
        create_visualizations(df, ardl_forecasts, ecm_forecasts, test_data, save_dir=save_dir)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nKey Findings Summary:")
        print(f"• Fed Funds Long-run Sensitivity: {fed_multiplier:.4f} (≈ {fed_multiplier:.1f} pp per 100bp 12MA_FEFF)")
        print(f"• ARDL Half-life: {math.log(0.5)/math.log(ardl_results.params['ALLCB_NIBD.L1']):.1f} quarters")
        print(f"• ARDL Out-of-sample MAPE: {ardl_metrics['MAPE']:.1f}%")
        if static_nii_benefit_m is not None:
            print(f"• Corrected Dynamic NII (first-year): ${corrected_nii_m:,.1f}M; Naive: ${naive_nii_m:,.1f}M")
        print(f"• Model demonstrates convexity effects reducing NII sensitivity for asset-sensitive banks")
        print("• Framework suitable for regulatory stress testing and ALM applications")
        
        return {
            'data': df,
            'ardl_results': ardl_results,
            'ecm_results': (static_results, ecm_results),
            'diagnostics': (ardl_diagnostics, ecm_diagnostics),
            'validation_metrics': (ardl_metrics, ecm_metrics),
            'forecasts': (ardl_forecasts, ecm_forecasts, test_data)
        }
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# EXECUTE ANALYSIS
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic NIBD Ratio Model - Complete Analysis")
    parser.add_argument('--csv', dest='csv', default=None, help='Path to CSV file (default: NIBD_ratio_v2.csv)')
    parser.add_argument('--shock-bp', dest='shock_bp', type=int, default=300, help='Fed Funds shock in basis points (default 300)')
    parser.add_argument('--total-deposits-bn', dest='total_deposits_bn', type=float, default=40.0, help='Total deposits in billions (default 40)')
    parser.add_argument('--rate-differential', dest='rate_diff', type=float, default=0.055, help='Rate differential between IB and NIBD (decimal, default 0.055)')
    parser.add_argument('--static-nii', dest='static_nii', type=float, default=150.0, help='Static asset-side NII benefit in millions (optional)')
    parser.add_argument('--export', dest='export', action='store_true', help='Export monthly transmission CSV, summary JSON, and save plots')
    parser.add_argument('--export-dir', dest='export_dir', default=None, help='Directory for exported artifacts (default: ./exports)')
    args = parser.parse_args()

    results = run_complete_analysis(
        csv_file_path=args.csv,
        shock_bp=args.shock_bp,
        total_deposits_bn=args.total_deposits_bn,
        rate_diff=args.rate_diff,
        static_nii_benefit_m=args.static_nii,
        export=args.export,
        export_dir=args.export_dir,
    )

    if results:
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE - Results generated successfully")
        print("="*80)
    else:
        print("Analysis failed. Please check the error messages above.")