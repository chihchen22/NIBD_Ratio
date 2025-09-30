# NIBD_Ratio
Econometric Model for Non-interest Bearing Deposit Ratio

## How to Import CSV Files

This repository includes tools to import CSV data for NIBD Ratio analysis.

### Prerequisites

Install required dependencies:
```bash
pip install pandas
```

### Quick Start

1. **Basic CSV Import**
```python
from csv_import import import_csv

# Import your CSV file
df = import_csv('your_data.csv')
print(df.head())
```

2. **Import with Options**
```python
# Import with custom delimiter and encoding
df = import_csv('data.csv', sep=';', encoding='latin-1')

# Import with date parsing
df = import_csv('data.csv', parse_dates=['date'], index_col='date')
```

3. **Import with Column Validation**
```python
from csv_import import import_csv_with_validation

# Ensure required columns exist
df = import_csv_with_validation(
    'data.csv', 
    required_columns=['date', 'nibd_ratio', 'total_deposits']
)
```

4. **Display Data Information**
```python
from csv_import import import_csv, display_csv_info

df = import_csv('data.csv')
display_csv_info(df)  # Shows shape, columns, types, stats, missing values
```

### Running the Example

Try the included example with sample data:
```bash
python example_usage.py
```

### CSV File Format

Your CSV file should contain relevant columns for NIBD analysis. Example format:

```csv
date,nibd_ratio,total_deposits,interest_rate,gdp_growth
2020-01-01,0.65,1000000,2.5,2.3
2020-02-01,0.67,1050000,2.4,2.2
```

A sample data file (`sample_data.csv`) is included for testing.

### Available Functions

- `import_csv(file_path, **kwargs)` - Import CSV file with pandas options
- `import_csv_with_validation(file_path, required_columns, **kwargs)` - Import with column validation
- `display_csv_info(df)` - Display comprehensive data information

### Common pandas.read_csv() Options

- `sep`: Delimiter (default: ',')
- `encoding`: File encoding (default: 'utf-8')
- `parse_dates`: Columns to parse as dates
- `index_col`: Column to use as row index
- `skiprows`: Number of rows to skip at the start
- `na_values`: Additional strings to recognize as NA/NaN

For more options, see the [pandas documentation](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html).
