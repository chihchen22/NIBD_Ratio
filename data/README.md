# Data Directory

This directory contains CSV files with econometric model data for calibration.

## Expected Data Format

Your CSV file should contain the data needed for the NIBD Ratio econometric model. Common columns might include:

- Date/Time period identifiers
- NIBD Ratio values (target variable)
- Economic indicators (independent variables)
- Other relevant features

## Adding Your Data

1. Place your CSV file(s) in this directory
2. Ensure the file is properly formatted with headers
3. Document any data preprocessing steps in the `docs/` directory

## Example

```
data/
├── nibd_calibration_data.csv    # Your main calibration dataset
├── nibd_test_data.csv           # Optional: test dataset
└── README.md                     # This file
```

## Note
CSV files are tracked by git. If you have large data files (>100MB), consider using Git LFS or documenting data sources externally.
