import os
import pandas as pd
from sqlalchemy import create_engine
from db_config import DB_CONNECTION_STR

def export_latest_panel():
    try:
        print("Connecting to database and retrieving data...")
        engine = create_engine(DB_CONNECTION_STR)

        query = "SELECT * FROM vw_firm_panel_latest;"
        
        df = pd.read_sql(query, con=engine)
        if df.empty:
            print("Caution: No data returned from the query!")
            return
        
        # Đổi tên cột cho chuẩn
        rename_mapping = {}
        if 'StockCode' in df.columns:
            rename_mapping['StockCode'] = 'ticker'
        if 'YearEnd' in df.columns:
            rename_mapping['YearEnd'] = 'fiscal_year'
            
        if rename_mapping:
            df = df.rename(columns=rename_mapping)
            
        cols = df.columns.tolist()
        if 'ticker' in cols and 'fiscal_year' in cols:
            cols.insert(0, cols.pop(cols.index('ticker')))
            cols.insert(1, cols.pop(cols.index('fiscal_year')))
            df = df[cols]
        
        output_dir = 'outputs'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir) 
        output_filepath = os.path.join(output_dir, 'panel_latest.csv')

        df.to_csv(output_filepath, index=False, encoding='utf-8-sig')
        
        print(f"EXPORTED SUCCESSFULLY! Saved {len(df)} lines of data at: {output_filepath}")
        
    except Exception as e:
        print(f"❌ ERROR:\n{e}")

if __name__ == "__main__":
    export_latest_panel()