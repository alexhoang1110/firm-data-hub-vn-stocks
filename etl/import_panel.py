import os
import pandas as pd
from sqlalchemy import create_engine, text
from create_snapshot import create_snapshot
from db_config import DB_CONNECTION_STR

# Change each of these values as needed for your specific import run
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
CONFIG_EXCEL_PATH = os.path.join(PROJECT_ROOT,'data', 'panel_2020_2024.xlsx')
CONFIG_SOURCE_ID = 1
CONFIG_FISCAL_YEAR = 2024
CONFIG_SNAPSHOT_DATE = '2026-03-03'
CONFIG_VERSION_TAG = 'v23'

FINANCIAL_MAP = {
    'Net sales revenue': 'net_sales',
    'Total assets': 'total_assets',
    'Selling expenses': 'selling_expenses',
    'General and administrative expenditure': 'general_admin_expenses',
    'Value of intangible assets': 'intangible_assets_net',
    'Manufacturing overhead (Indirect cost)': 'manufacturing_overhead',
    'Net operating income': 'net_operating_income',
    'Consumption of raw material': 'raw_material_consumption',
    'Merchandise purchase of the year': 'merchandise_purchase_year',
    'Work-in-progess goods purchase': 'wip_goods_purchase',
    'Outside manufacturing expenses': 'outside_manufacturing_expenses',
    'Production cost': 'production_cost',
    'R&D expenditure': 'rnd_expenses',
    'Net Income': 'net_income',
    "Total shareholders' equity": 'total_equity',
    'Total liabilities': 'total_liabilities',
    'Cash and cash equivalent': 'cash_and_equivalents',
    'Long-term debt': 'long_term_debt',
    'Current assets': 'current_assets',
    'Current liabilities': 'current_liabilities',
    'Growth ratio': 'growth_ratio',
    'Total inventory': 'inventory',
    'Net plant, property and equipment': 'net_ppe'
}

MARKET_MAP = {
    'Total shares outstanding': 'shares_outstanding',
    'Market price per share': 'market_price_per_share',
    'Dividend payment': 'dividend_cash_paid',
    'EPS(VND)': 'eps_basic'
}

OWNERSHIP_MAP = {
    'Managerial/Inside ownership': 'managerial_inside_own',
    'State ownership': 'state_own',
    'Institutional ownership': 'institutional_own',
    'Foreign ownership': 'foreign_own'
}

CASHFLOW_MAP = {
    'Net cash from operating activities': 'net_cfo',
    'Capital expenditure': 'capex',
    'Cash flows from investing activities': 'net_cfi'
}

META_MAP = {
    'Number of employees': 'employees_count',
    'Firm age': 'firm_age'
}

INNOVATION_MAP = {
    'Product innovation': 'product_innovation',
    'Process innovation': 'process_innovation'
}

def get_firm_mapping(engine):
    query = "SELECT ticker, firm_id FROM dim_firm;"
    with engine.connect() as connection:
        result = connection.execute(text(query))
        return {row[0]: row[1] for row in result.fetchall()}
    
def clean_numeric_data(val):
    if pd.isna(val):
        return val
    if isinstance(val, (int, float)):
        return val
    
    val_str = str(val).strip().replace('%', '')

    if ',' in val_str and '.' in val_str:
        if val_str.find('.') > val_str.find(','):
            val_str = val_str.replace(',', '')
        else:
            val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
        
    try:
        return float(val_str)
    except ValueError:
        return None
    
def process_and_upload(df, engine, mapping_dict, table_name, base_cols):
    available_cols = {k: v for k, v in mapping_dict.items() if k in df.columns}

    if not available_cols:
        return
    
    df_subset = df[base_cols + list(available_cols.keys())].copy()
    df_subset.rename(columns = available_cols, inplace = True)

    df_subset.to_sql(table_name, con = engine, if_exists = 'append', index = False)


def main():
    engine = create_engine(DB_CONNECTION_STR)

    snapshot_id = create_snapshot(
        source_id = CONFIG_SOURCE_ID,
        fiscal_year = CONFIG_FISCAL_YEAR,
        snapshot_date = CONFIG_SNAPSHOT_DATE,
        version_tag = CONFIG_VERSION_TAG
    )

    df = pd.read_excel(CONFIG_EXCEL_PATH)
    df.columns = df.columns.str.strip()

    print(f"Total rows in Excel: {len(df)}")

    for col in df.columns:
        if col not in ['StockCode', 'YearEnd', 'Industry', 'Exchange']:
            df[col] = df[col].apply(clean_numeric_data)
    
    ownership_cols = ['Managerial/Inside ownership', 'State ownership', 'Institutional ownership', 'Foreign ownership']
    for col in ownership_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x / 100.0 if pd.notna(x) and abs(x) > 1 else x)

    if 'Growth ratio' in df.columns:
        df['Growth ratio'] = df['Growth ratio'] / 100.0

    firm_map = get_firm_mapping(engine)
    print(f"Firm mapping dictionary: {firm_map}")

    df['firm_id'] = df['StockCode'].map(firm_map)

    unmapped_tickers = df[df['firm_id'].isna()]['StockCode'].unique()
    print(f"Tickers not found in DB: {unmapped_tickers}")

    df = df.dropna(subset = ['firm_id'])
    print(f"Total rows after mapping firm_id: {len(df)}")

    if len(df) == 0:
        print("ERROR: DataFrame is empty. Halting upload.")
        return

    df['snapshot_id'] = snapshot_id
    df['fiscal_year'] = df['YearEnd']

    base_columns = ['firm_id', 'fiscal_year', 'snapshot_id']
    
    process_and_upload(df, engine, FINANCIAL_MAP, 'fact_financial_year', base_columns)
    process_and_upload(df, engine, MARKET_MAP, 'fact_market_year', base_columns)
    process_and_upload(df, engine, OWNERSHIP_MAP, 'fact_ownership_year', base_columns)
    process_and_upload(df, engine, CASHFLOW_MAP, 'fact_cashflow_year', base_columns)
    process_and_upload(df, engine, META_MAP, 'fact_firm_year_meta', base_columns)
    process_and_upload(df, engine, INNOVATION_MAP, 'fact_innovation_year', base_columns)

if __name__ == "__main__":
    main()