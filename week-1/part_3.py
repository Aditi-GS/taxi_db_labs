import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
import pandas as pd
import os

file_path = "yellow_tripdata_2025-06.parquet"
df_raw = pd.read_parquet(file_path)
df_raw.columns = [col.lower() for col in df_raw.columns]

df = df_raw.rename(columns={
    "vendorid": "vendor_id",
    "ratecodeid": "ratecode_id",
    "pulocationid": "pu_location_id",
    "dolocationid": "do_location_id"
})

print(f"Rows, Columns = {df.shape}")

# first 100k rows for testing
subset = df.head(100_000)
CSV_FILE = r"yellow_tripdata_subset.csv"
subset.to_csv(f"{CSV_FILE}", index=False)

conn = psycopg2.connect(
    host=settings.db_host,
    database=settings.db_name,
    user=settings.db_username,
    password=settings.db_password,
    port=settings.db_port,
    cursor_factory=RealDictCursor
)
cursor = conn.cursor()
print("DB connection successful!")

cols = subset.columns

## <--------------------    BULK COPY (Streaming)     -------------------->
abs_csv_path = os.path.abspath(CSV_FILE)

copy_sql = f"""
COPY trips({','.join(cols)})
FROM STDIN
WITH CSV HEADER DELIMITER ','
"""

try:
    with open(abs_csv_path, 'r') as f:
        cursor.copy_expert(copy_sql, f)
    conn.commit()
    print("Load successful!")
except Exception as e:
    conn.rollback()
    print(f"Load failed, rolled back: {e}")
    raise

# print("\nCLEANUP\n")
# cursor.execute("""TRUNCATE TABLE trips RESTART IDENTITY;""")
# conn.commit()