## Project Overview

Firm Data Hub is a centralized data warehouse system designed to store, perform quality control (QC), manage versions (snapshots), and export panel data for 20 listed companies in Vietnam over a 5-year period (2020-2024)

This project is the Midterm Project for the SQL course, demonstrating a complete Data Engineering pipeline from raw data extraction to a structured `DIM + FACT + SNAPSHOT` relational database on MySQL

## Team Members & Contribution

| Team Member           | Student ID | Role            | Main Responsibilities & Tasks Completed                                                                                                  | Contribution (%) |
| --------------------- | ---------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **Hoang Linh Phuong** | 11245925   | Team Leader<br> | - Built the complete Python ETL pipeline (Import, QC, Snapshot, Export).<br>- Co-designed the database schema and system configurations. | 25.6             |
| **Duong Hong Anh**    | 11245842   | Team Member     | - Co-designed the database schema.<br>- Developed SQL master views and validation queries for data auditing.                             | 25.6             |
| **Le Thuy Duong**     | 11245864   | Team Member     | - Conducted data sourcing and managed manual data entry for the panel dataset.<br>- Performed data collection dry runs.                  | 25.6             |
| **Ngo Thi Tuyet Mai** | 1245903    | Team Member     | - Standardized raw financial data from various sources.<br>- Executed manual data entry for the 2020-2024 panel dataset.                 | 23               |
## Data Scope & Sources

- **Tickers:** 20 assigned stock tickers (including SAB, PTC, TRA, etc.)
- **Timeframe:** 2020 - 2024
- **Variables:** 38 variables covering Ownership, Market, Financial Statements, Cashflow, Innovation, and Metadata
- **Data Source:** 
	- Financial reports & Market data automatically fetched via the `vnstock` library.
	- Audited Financial Statements & Annual Reports.
	- *Manual Data Entry Note:* Specific variables such as "Process/Product Innovation" and missing historical liabilities/assets were manually verified and imputed based on official consolidated financial statements.

## Database Architecture

The database is hosted on Aiven Cloud (MySQL) and strictly follows the required dimensional modeling:
- **Dimensions (DIM):** `dim_firm`, `dim_exchange`, `dim_industry_12`, `dim_data_source`.
- **Snapshot:** `fact_data_snapshot` (for version control).
- **Facts:** `fact_ownership_year`, `fact_financial_year`, `fact_cashflow_year`, `fact_market_year`, `fact_innovation_year`, `fact_firm_year_meta`.
- **Views:** `vw_firm_panel` (Generates the final clean dataset).

## Prerequisites

To reproduce this pipeline, ensure you have the following installed:
- Python 3.9+
- MySQL Server (or an active Aiven Cloud connection)
- Required Python libraries: See in Python file `requirements.py`

*Note: Configure your database connection in `db_config.py` (DB_USER, DB_PASS, DB_HOST) before running the scripts.*

## ETL Pipeline & How to Run

The system is built to be 100% reproducible. Please run the scripts in the `etl/` directory in the following exact order.

### Step 1: Initialize Database

Run the SQL script to create the schema, tables, and views:

```Plaintext
mysql -u <username> -p < sql/vn_firm_panel.sql
```

### Step 2: Import Firms

Populates the DIM tables with the 20 assigned companies from `data/firms.xlsx`.

```Plaintext
python etl/import_firms.py
```

### Step 3: Create Snapshot & Import Panel Data

Generates a new snapshot ID and ingests the 38 variables from `data/panel_2020_2024.xlsx` into the FACT tables.

```Plaintext
python etl/import_panel.py
```

### Step 4: Quality Control (QC) Checks

Validates the data against strictly defined accounting and logical rules (e.g., Total Assets >= 0, Accounting Equation checks). It outputs a report to `outputs/qc_report.csv`.

```Plaintext
python etl/qc_checks.py
```

### Step 5: Export Latest Clean Panel

Extracts the latest snapshot for each firm-year through the `vw_firm_panel_latest` view and exports the final 38-variable dataset to `outputs/panel_latest.csv`.

```Plaintext
python etl/export_panel.py
```

## Directory Structure

```Plaintext
TEAM_6_FirmDataHub/
├── data/
│   ├── team_tickers.csv       # List of 20 assigned tickers
│   ├── firms.xlsx             # Company metadata
│   └── panel_2020_2024.xlsx   # Raw dataset (5 years x 38 variables)
├── etl/
│   ├── db_config.py           # Database connection string
│   ├── import_firms.py        # Script A
│   ├── create_snapshot.py     # Script B
│   ├── import_panel.py        # Script C
│   ├── qc_checks.py           # Data validation script
│   └── export_panel.py        # Final export script
├── outputs/
│   ├── qc_report.csv          # Generated QC error log
│   └── panel_latest.csv       # Final output dataset
├── sql/
│   └── schema_and_seed.sql    # DDL constraints and views
└── README.md                  # This documentation
```
