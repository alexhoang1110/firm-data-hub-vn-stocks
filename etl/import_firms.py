import os
import pandas as pd
from sqlalchemy import create_engine, text
from db_config import DB_CONNECTION_STR

# 1. READ DATA FROM EXCEL FILE

print("Reading Excel file...")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
CONFIG_EXCEL_PATH = os.path.join(PROJECT_ROOT,'data', 'firms.xlsx')

df = pd.read_excel(CONFIG_EXCEL_PATH, usecols = ['Firms', 'Ticker', 'Industry', 'Exchange'])

# 2. DATA CLEANING

unique_firms = df.drop_duplicates(subset = ['Ticker']).copy()

# Standardization
unique_firms.rename(columns = {'Firms': 'firm_name', 'Ticker': 'ticker', 'Industry': 'industry_name', 'Exchange': 'exchange_name'}, inplace = True)

# 3. CONNECT WITH DATABASE & DATA IMPORT
engine = create_engine(DB_CONNECTION_STR)

try:
    with engine.connect() as connection:
        print("Connect to the database successfully! Start importing...")

        connection.execute(text("INSERT IGNORE INTO dim_exchange (exchange_code) VALUES ('HOSE'), ('HNX'), ('UPCOM'), ('OTC')"))

        # Step 1: Automatic Industry Updates (dim_industry_l2)
        industries = unique_firms['industry_name'].unique()

        for ind_name in industries:
            if pd.isna(ind_name): continue # Skip if blank
            
            # SQL queries (Using for MySQL only)
            sql_industry = text("""
                INSERT IGNORE INTO dim_industry_l2 (industry_l2_name)
                VALUES (:name)
            """)
            connection.execute(sql_industry, {"name": ind_name})
        print("Update Industry categories successfully!")

        # Step 2: Insert Firm Name (dim_firm)
        count = 0
        for index, row in unique_firms.iterrows():
            ticker = row['ticker']
            name = row['firm_name']
            ind_name = row['industry_name']
            exc_name = row['exchange_name']

            # Find Industry ID
            ind_id = None
            if pd.notna(ind_name):
                result = connection.execute(text("SELECT industry_l2_id FROM dim_industry_l2 WHERE industry_l2_name = :n"), {"n": ind_name})
                ind_id_row = result.fetchone()
                ind_id = ind_id_row[0] if ind_id_row else None
            
            # Find Exchange ID
            exc_id = None
            if pd.notna(exc_name):
                result = connection.execute(text("SELECT exchange_id FROM dim_exchange WHERE exchange_code = :n"), {"n": exc_name})
                exc_id_row = result.fetchone()
                exc_id = exc_id_row[0] if exc_id_row else None
            
            if exc_id is None:
                print(f"Warning: Exchange ID not found for {ticker} ({exc_name})")
    
            # SQL queries
            sql_firm = text("""
                INSERT INTO dim_firm (ticker, company_name, industry_l2_id, exchange_id)
                VALUES (:code, :name, :ind_id, :exc_id)
                ON DUPLICATE KEY UPDATE company_name = :name, industry_l2_id = :ind_id, exchange_id = :exc_id
                """)
                
            connection.execute(sql_firm, {"code": ticker, "name": name, "ind_id": ind_id, "exc_id": exc_id})
            count += 1
        
        connection.commit() # Save the change
        print(f"FINISH! {count} firms imported into database.")

except Exception as e:
    print(" ERROR:")
    print(e)