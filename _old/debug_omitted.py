#!/usr/bin/env python3
"""
Debug script to analyze omitted results
"""

import pandas as pd
import os

def analyze_omitted_results():
    file_path = 'omitidos/omitidos_011901.1_Pea_farms_to_011901.1_Pea_farms_20250719_224912.xlsx'

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)

        print('Available columns:')
        print(df.columns.tolist())
        print()

        # Show a few examples
        if len(df) > 0:
            print('First few entries:')
            for i in range(min(5, len(df))):
                row = df.iloc[i]
                url_col = [col for col in df.columns if 'link' in col.lower() or 'url' in col.lower()]
                if url_col:
                    url = row.get(url_col[0], 'N/A')
                    print(f'{i+1}. URL: {url}')
                    print(f'   Title: {row.get("Title", "N/A")}')
                    print(f'   Description: {row.get("Description", "N/A")}')
                    print(f'   Omission Reason: {row.get("Reason for Omission")}')
                    print()
    else:
        print(f'File not found: {file_path}')

if __name__ == "__main__":
    analyze_omitted_results()