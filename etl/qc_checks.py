import os
import pandas as pd
from sqlalchemy import create_engine, text
from db_config import DB_CONNECTION_STR

def run_query(engine, query, params = None):
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        return pd.DataFrame(result.fetchall(), columns = result.keys())
    
def get_qc_errors(engine, snapshot_id):
    error_logs = []

    # 1. Logic Errors
    query_fin = """
        SELECT d.ticker, f.fiscal_year, f.total_assets, f.total_equity, f.total_liabilities, f.net_sales, f.net_income
        FROM fact_financial_year f
        JOIN dim_firm d ON f.firm_id = d.firm_id
        WHERE f.snapshot_id = :sid
    """
    df_fin = run_query(engine, query_fin, {'sid': snapshot_id})
    for _, row in df_fin.iterrows():
        # Check if Total Assets = Total Equity + Total Liabilities
        if pd.notna(row['total_assets']) and pd.notna(row['total_equity']) and pd.notna(row['total_liabilities']):
            diff = abs(row['total_assets'] - (row['total_equity'] + row['total_liabilities']))
            if diff > 2.0:
                error_logs.append({
                    "type": "Logic Error",
                    "ticker": row['ticker'],
                    "fiscal_year": row['fiscal_year'],
                    "message": f"Total Assets do not equal Equity + Liabilities (Difference: {diff:.2f})"
                })
        # NULL error checks
        for col in ['net_sales', 'total_assets', 'net_income']:
            if pd.isna(row[col]):
                error_logs.append({
                    'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'column': col, 'message': f"{col} is NULL"})
                
    # 2. QC Rules
    query_fin_qc = """
        SELECT d.ticker, f.fiscal_year, f.total_assets, f.current_liabilities, f.growth_ratio
        FROM fact_financial_year f
        JOIN dim_firm d ON f.firm_id = d.firm_id
        WHERE f.snapshot_id = :sid
    """
    df_fin_qc = run_query(engine, query_fin_qc, {'sid': snapshot_id})
    for _, row in df_fin_qc.iterrows():
        # Total assets >= 0
        if pd.notna(row['total_assets']) and row['total_assets'] < 0:
            error_logs.append({'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'field_name': 'total_assets', 'error_type': 'QC Rule Violation', 'message': f"Total assets < 0 ({row['total_assets']})"})
        # Current liabilities >= 0
        if pd.notna(row['current_liabilities']) and row['current_liabilities'] < 0:
            error_logs.append({'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'field_name': 'current_liabilities', 'error_type': 'QC Rule Violation', 'message': f"Current liabilities < 0 ({row['current_liabilities']})"})
        # Growth ratio [-0.95, 5.0]
        if pd.notna(row['growth_ratio']) and (row['growth_ratio'] < -0.95 or row['growth_ratio'] > 5.0):
            error_logs.append({'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'field_name': 'growth_ratio', 'error_type': 'QC Rule Violation', 'message': f"Growth ratio out of bounds ({row['growth_ratio']})"})
    # Rule 1: Ownership
    query_own_qc = """
        SELECT d.ticker, o.fiscal_year, o.managerial_inside_own, o.state_own, o.institutional_own, o.foreign_own
        FROM fact_ownership_year o
        JOIN dim_firm d ON o.firm_id = d.firm_id
        WHERE o.snapshot_id = :sid
    """
    df_own = run_query(engine, query_own_qc, {'sid': snapshot_id})
    for _, row in df_own.iterrows():
        for col in ['managerial_inside_own', 'state_own', 'institutional_own', 'foreign_own']:
            if pd.notna(row[col]) and (row[col] < 0 or row[col] > 1):
                error_logs.append({'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'field_name': col, 'error_type': 'QC Rule Violation', 'message': f"{col} out of bounds ({row[col]})"})
    # Rule 2: Market Data
    query_market_qc = """
        SELECT d.ticker, m.fiscal_year, m.shares_outstanding
        FROM fact_market_year m
        JOIN dim_firm d ON m.firm_id = d.firm_id
        WHERE m.snapshot_id = :sid
    """
    df_mkt = run_query(engine, query_market_qc, {'sid': snapshot_id})
    for _, row in df_mkt.iterrows():
        if pd.notna(row['shares_outstanding']) and row['shares_outstanding'] <= 0:
            error_logs.append({'ticker': row['ticker'], 'fiscal_year': row['fiscal_year'], 'field_name': 'shares_outstanding', 'error_type': 'QC Rule Violation', 'message': f"Shares outstanding <= 0 ({row['shares_outstanding']})"})

    return error_logs

def get_latest_snapshot_id(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT MAX(snapshot_id) FROM fact_data_snapshot"))
        return result.scalar()

def main():
    engine = create_engine(DB_CONNECTION_STR)
    latest_snapshot_id = get_latest_snapshot_id(engine)
    errors = get_qc_errors(engine, latest_snapshot_id)

    if not os.path.exists('outputs'):
        os.makedirs('outputs')

    report_df = pd.DataFrame(errors, columns = ['ticker', 'fiscal_year', 'field_name', 'error_type', 'message'])
    output_path = 'outputs/qc_report.csv'
    report_df.to_csv(output_path, index = False, encoding = 'utf-8-sig')

    if len(errors) > 0:
        print(f"QC checks completed with {len(errors)} errors found. Report saved to {output_path}")
    else:
        print("QC checks completed with no errors found.")

if __name__ == "__main__":
    main()