from sqlalchemy import create_engine, text
from db_config import DB_CONNECTION_STR

def create_snapshot(source_id, fiscal_year, snapshot_date, version_tag):
    engine = create_engine(DB_CONNECTION_STR)
    sql_insert = text("INSERT INTO fact_data_snapshot (source_id, fiscal_year, snapshot_date, version_tag) VALUES (:source, :year, :date, :tag);")
    sql_get_id = text("SELECT LAST_INSERT_ID();")

    try:
        with engine.begin() as connection:
            connection.execute(sql_insert, {"source": source_id, "year": fiscal_year,"date": snapshot_date,"tag": version_tag})
            result = connection.execute(sql_get_id)
            snapshot_id = result.scalar()

            print(f"New snapshot created! ID: {snapshot_id}")
            return snapshot_id
    except Exception as e:
        print(f"ERROR: {e}")
        return None

# TEST CASE
if __name__ == "__main__":
    test_id = create_snapshot(
        source_id=1, 
        fiscal_year=2024,
        snapshot_date="2026-02-15",
        version_tag="Test_Run_1"
    )
    print(f"Returned Result: {test_id}")