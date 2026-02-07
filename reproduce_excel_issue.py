
import pandas as pd
import io

def test_excel_reading():
    print("Creating test Excel file with leading zero...")
    # Create a DataFrame with leading zeros
    data = {'Code': ['01.0', '007', '10.5'], 'Name': ['Test1', 'Test2', 'Test3']}
    df_orig = pd.DataFrame(data)
    
    # Save to BytesIO as Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_orig.to_excel(writer, index=False)
    excel_data = output.getvalue()
    
    print("\nReading back with default settings (should fail/convert):")
    try:
        df_default = pd.read_excel(io.BytesIO(excel_data))
        print(df_default)
        print("Data types:")
        print(df_default.dtypes)
    except Exception as e:
        print(e)
        
    print("\nReading back with dtype=str (should preserve):")
    try:
        df_str = pd.read_excel(io.BytesIO(excel_data), dtype=str)
        print(df_str)
        print("Data types:")
        print(df_str.dtypes)
        
        val = df_str.iloc[0, 0]
        print(f"\nValue at [0,0]: '{val}' (Type: {type(val)})")
        
        if val == "01.0":
            print("✅ SUCCESS: Leading zero preserved.")
        else:
            print(f"❌ FAILURE: Expected '01.0', got '{val}'")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_excel_reading()
