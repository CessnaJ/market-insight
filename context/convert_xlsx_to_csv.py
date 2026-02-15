#!/usr/bin/env python3
"""
KIS OpenAPI Excel to CSV Converter
Converts 한국투자증권_오픈API_전체문서.xlsx to CSV format
"""

import pandas as pd
import sys
from pathlib import Path

def convert_xlsx_to_csv(xlsx_path: str, output_dir: str = None):
    """
    Convert Excel file to CSV format
    
    Args:
        xlsx_path: Path to the Excel file
        output_dir: Output directory (default: same as input file)
    """
    xlsx_file = Path(xlsx_path)
    
    if not xlsx_file.exists():
        print(f"Error: File not found: {xlsx_path}")
        sys.exit(1)
    
    # Set output directory
    if output_dir is None:
        output_dir = xlsx_file.parent
    else:
        output_dir = Path(output_dir)
    
    # Read Excel file with all sheets
    try:
        excel_file = pd.ExcelFile(xlsx_file)
        sheet_names = excel_file.sheet_names
        
        print(f"Found {len(sheet_names)} sheet(s): {sheet_names}")
        print()
        
        for sheet_name in sheet_names:
            # Read sheet
            df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
            
            # Generate CSV filename
            csv_filename = f"{xlsx_file.stem}_{sheet_name}.csv"
            csv_path = output_dir / csv_filename
            
            # Save to CSV
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            print(f"✓ Converted: {sheet_name} -> {csv_filename}")
            print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
            print()
        
        print("Conversion complete!")
        
    except Exception as e:
        print(f"Error converting file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Default file path
    default_xlsx = "한국투자증권_오픈API_전체문서_20260215_030000.xlsx"
    
    # Use command line argument if provided
    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else default_xlsx
    
    print(f"Converting: {xlsx_path}")
    print("=" * 50)
    print()
    
    convert_xlsx_to_csv(xlsx_path)
