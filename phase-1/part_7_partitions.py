import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
import pandas as pd
import io

file_path = "yellow_tripdata_2025-06.parquet"
df_raw = pd.read_parquet(file_path)
df_raw.columns = [col.lower() for col in df_raw.columns]

df = df_raw.rename(columns={
    "vendorid": "vendor_id",
    "ratecodeid": "ratecode_id",
    "pulocationid": "pu_location_id",
    "dolocationid": "do_location_id"
})
# free memory immediately
del df_raw

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

cols = df.columns

buffer = io.BytesIO()
df.to_csv(buffer, index=False, encoding="utf-8")
# once buffer loaded, DataFrame no longer required
del df
buffer.seek(0)

copy_sql = f"""
COPY trips_partitioned({','.join(cols)})
FROM STDIN
WITH CSV HEADER DELIMITER ','
"""

try:
    cursor.copy_expert(copy_sql, buffer)
    conn.commit()
    print("Load successful!")
except Exception as e:
    conn.rollback()
    print(f"Load failed, rolled back: {e}")
    raise
finally:
    cursor.close()
    conn.close()    