"""
Example Usage Script for CSV Import

This script demonstrates how to import and use CSV data
for NIBD Ratio analysis.
"""

from csv_import import import_csv, import_csv_with_validation, display_csv_info


def main():
    print("NIBD Ratio - CSV Import Example\n")
    
    # Example 1: Basic CSV import
    print("Example 1: Basic CSV Import")
    print("-" * 50)
    try:
        df = import_csv('sample_data.csv')
        print(f"Successfully imported {len(df)} rows of data")
        print(f"Columns: {list(df.columns)}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 2: Import with date parsing
    print("\nExample 2: Import with Date Parsing")
    print("-" * 50)
    try:
        df = import_csv('sample_data.csv', parse_dates=['date'], index_col='date')
        print(f"Data imported with date index")
        print(f"Date range: {df.index.min()} to {df.index.max()}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 3: Import with validation
    print("\nExample 3: Import with Column Validation")
    print("-" * 50)
    try:
        required_cols = ['date', 'nibd_ratio', 'total_deposits']
        df = import_csv_with_validation('sample_data.csv', 
                                        required_columns=required_cols)
        print(f"Data validated successfully")
        print(f"All required columns present: {required_cols}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 4: Display comprehensive data information
    print("\nExample 4: Comprehensive Data Information")
    print("-" * 50)
    try:
        df = import_csv('sample_data.csv', parse_dates=['date'])
        display_csv_info(df)
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 5: Basic data analysis
    print("\nExample 5: Basic Analysis on NIBD Ratio")
    print("-" * 50)
    try:
        df = import_csv('sample_data.csv')
        print(f"Average NIBD Ratio: {df['nibd_ratio'].mean():.4f}")
        print(f"Min NIBD Ratio: {df['nibd_ratio'].min():.4f}")
        print(f"Max NIBD Ratio: {df['nibd_ratio'].max():.4f}")
        print(f"Std Dev: {df['nibd_ratio'].std():.4f}")
    except Exception as e:
        print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
