"""
CSV Import Module for NIBD Ratio Analysis

This module provides functions to import CSV data files for 
Non-interest Bearing Deposit Ratio econometric modeling.
"""

import pandas as pd
import os


def import_csv(file_path, **kwargs):
    """
    Import a CSV file and return a pandas DataFrame.
    
    Parameters:
    -----------
    file_path : str
        Path to the CSV file to import
    **kwargs : dict
        Additional arguments to pass to pandas.read_csv()
        Common options:
        - sep: delimiter (default: ',')
        - encoding: file encoding (default: 'utf-8')
        - parse_dates: columns to parse as dates
        - index_col: column to use as index
        
    Returns:
    --------
    pandas.DataFrame
        The imported data as a DataFrame
        
    Raises:
    -------
    FileNotFoundError
        If the specified file does not exist
    ValueError
        If the file is empty or improperly formatted
        
    Example:
    --------
    >>> df = import_csv('data.csv')
    >>> df = import_csv('data.csv', sep=';', encoding='latin-1')
    >>> df = import_csv('data.csv', parse_dates=['date'], index_col='date')
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        df = pd.read_csv(file_path, **kwargs)
        
        if df.empty:
            raise ValueError(f"The CSV file is empty: {file_path}")
            
        return df
        
    except pd.errors.EmptyDataError:
        raise ValueError(f"The CSV file is empty: {file_path}")
    except pd.errors.ParserError as e:
        raise ValueError(f"Error parsing CSV file: {e}")


def import_csv_with_validation(file_path, required_columns=None, **kwargs):
    """
    Import a CSV file with column validation.
    
    Parameters:
    -----------
    file_path : str
        Path to the CSV file to import
    required_columns : list, optional
        List of column names that must be present in the CSV
    **kwargs : dict
        Additional arguments to pass to pandas.read_csv()
        
    Returns:
    --------
    pandas.DataFrame
        The imported data as a DataFrame
        
    Raises:
    -------
    ValueError
        If required columns are missing from the CSV
        
    Example:
    --------
    >>> df = import_csv_with_validation('data.csv', 
    ...                                  required_columns=['date', 'nibd_ratio'])
    """
    df = import_csv(file_path, **kwargs)
    
    if required_columns:
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )
    
    return df


def display_csv_info(df):
    """
    Display basic information about the imported CSV data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame to display information about
        
    Example:
    --------
    >>> df = import_csv('data.csv')
    >>> display_csv_info(df)
    """
    print("=" * 50)
    print("CSV Data Information")
    print("=" * 50)
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\nColumns: {', '.join(df.columns.tolist())}")
    print("\nData types:")
    print(df.dtypes)
    print("\nFirst few rows:")
    print(df.head())
    print("\nBasic statistics:")
    print(df.describe())
    print("\nMissing values:")
    print(df.isnull().sum())
    print("=" * 50)


if __name__ == "__main__":
    # Example usage
    print("CSV Import Module for NIBD Ratio Analysis")
    print("\nUsage examples:")
    print("1. Basic import:")
    print("   df = import_csv('data.csv')")
    print("\n2. Import with options:")
    print("   df = import_csv('data.csv', sep=';', encoding='latin-1')")
    print("\n3. Import with validation:")
    print("   df = import_csv_with_validation('data.csv', required_columns=['date', 'nibd_ratio'])")
    print("\n4. Display data info:")
    print("   display_csv_info(df)")
