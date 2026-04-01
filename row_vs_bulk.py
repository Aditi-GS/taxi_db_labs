import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
import pandas as pd
from time import time
import os

"""
METRICS:
1. Insert Time
2. WAL Growth
3. DB Size
"""

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

def get_wal_lsn():
    cursor.execute("""SELECT pg_current_wal_lsn()""")
    return cursor.fetchone()['pg_current_wal_lsn']

def get_db_size():
    cursor.execute("""SELECT pg_size_pretty(pg_database_size(%s))""", (settings.db_name,))
    # just cursor.fetchone() returns a RealDictRow like {'pg_size_pretty': '8350 kB'}
    return cursor.fetchone()['pg_size_pretty']

def get_wal_diff(start_lsn, end_lsn):
    cursor.execute("""SELECT pg_size_pretty(pg_wal_lsn_diff(%s, %s))""", (end_lsn, start_lsn))
    return cursor.fetchone()['pg_size_pretty']

### ROW-BY-ROW INSERT -> lots of small WAL writes -> slower
start_time = time()
start_lsn = get_wal_lsn()
start_db_size = get_db_size()

print("\nROW-BY-ROW INSERT\n")
for idx, row in subset.iterrows():
    cursor.execute(
        f"""
        INSERT INTO trips ({','.join(cols)})
        VALUES ({','.join(['%s']*len(cols))})
        """,
        tuple(row[col] for col in cols)
    )
conn.commit()

end_time = time()
end_lsn = get_wal_lsn()
end_db_size = get_db_size()

row_by_row_metrics = {
    "time_sec": round(end_time - start_time, 2),
    "wal_written": get_wal_diff(start_lsn, end_lsn),
    "ini_db_size": start_db_size,
    "db_size": end_db_size
}

print(row_by_row_metrics)

print("\nCLEANUP\n")
cursor.execute("""TRUNCATE TABLE trips RESTART IDENTITY;""")
conn.commit()

### BULK INSERT -> fewer, larger WAL writes -> faster
abs_csv_path = os.path.abspath(CSV_FILE)
start_time = time()
start_lsn = get_wal_lsn()
start_db_size = get_db_size()

print("\nBULK INSERT\n")
copy_sql = f"""
COPY trips({','.join(cols)})
FROM STDIN
WITH CSV HEADER DELIMITER ','
"""
with open(abs_csv_path, 'r') as f:
    cursor.copy_expert(copy_sql, f)
conn.commit()

end_time = time()
end_lsn = get_wal_lsn()
end_db_size = get_db_size()

bulk_metrics = {
    "time_sec": round(end_time - start_time, 2),
    "wal_written": get_wal_diff(start_lsn, end_lsn),
    "ini_db_size": start_db_size,
    "db_size": end_db_size
}

print("\nCLEANUP\n")
cursor.execute("""TRUNCATE TABLE trips RESTART IDENTITY;""")
conn.commit()

print("\n=== ROW BY ROW ===")
print(row_by_row_metrics)
print("\n=== BULK ===")
print(bulk_metrics)