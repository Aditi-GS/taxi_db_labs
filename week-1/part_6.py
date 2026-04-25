import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
import pandas as pd
from time import time
import os

"""
METRICS:
1. Insert Time
2. WAL writes
3. DB Size
4. WAL writes (buffer -> OS page cache)
5. WAL fsyncs (OS page cache -> Disk)
6. WAL buffer flushes count
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

def set_synchronous_commit(value: str):
    conn.rollback()  # close any open transaction first (safety)
    conn.autocommit = True
    cursor.execute(f"ALTER SYSTEM SET synchronous_commit = {value};")
    cursor.execute("SELECT pg_reload_conf();")
    conn.autocommit = False

def get_wal_lsn():
    cursor.execute("""SELECT pg_current_wal_lsn()""")
    return cursor.fetchone()['pg_current_wal_lsn']

def get_db_size():
    cursor.execute("""SELECT pg_size_pretty(pg_database_size(%s))""", (settings.db_name,))
    return cursor.fetchone()['pg_size_pretty']

def get_wal_diff(start_lsn, end_lsn):
    cursor.execute("""SELECT pg_size_pretty(pg_wal_lsn_diff(%s, %s))""", (end_lsn, start_lsn))
    return cursor.fetchone()['pg_size_pretty']

def enable_wal_io_tracking():
    conn.autocommit = True
    cursor.execute("""ALTER SYSTEM SET track_wal_io_timing = on;""")
    cursor.execute("""SELECT pg_reload_conf();""")
    conn.autocommit = False

def get_wal_stats():
    cursor.execute("""
        SELECT
            COALESCE(SUM(writes), 0)      AS wal_write,
            COALESCE(SUM(write_bytes), 0) AS wal_write_bytes,
            COALESCE(SUM(write_time), 0)  AS wal_write_time,
            COALESCE(SUM(fsyncs), 0)      AS wal_sync,
            COALESCE(SUM(fsync_time), 0)  AS wal_sync_time
        FROM pg_stat_io
        WHERE object = 'wal'
    """)
    io_row = dict(cursor.fetchone())

    cursor.execute("""
        SELECT wal_buffers_full
        FROM pg_stat_wal
    """)
    wal_row = dict(cursor.fetchone())

    return {**io_row, **wal_row}

def delta_wal_stats(start, end):
    return {
        "wal_buffers_full":  end['wal_buffers_full']  - start['wal_buffers_full'],
        "wal_write":         end['wal_write']          - start['wal_write'],
        "wal_write_bytes":   end['wal_write_bytes']    - start['wal_write_bytes'],
        "wal_write_time_ms": round(end['wal_write_time'] - start['wal_write_time'], 2),
        "wal_sync":          end['wal_sync']           - start['wal_sync'],
        "wal_sync_time_ms":  round(end['wal_sync_time']  - start['wal_sync_time'], 2),
    }

def reset_wal_stats():
    conn.autocommit = True
    cursor.execute("SELECT pg_stat_reset_shared('wal')")
    cursor.execute("SELECT pg_stat_reset_shared('io')")
    conn.autocommit = False

def run_case_a():
    reset_wal_stats()
    try:
        set_synchronous_commit('off')
        start_time = time()
        start_lsn = get_wal_lsn()
        start_db_size = get_db_size()
        start_wal_stats = get_wal_stats()

        print("\nCASE A\n")
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
        end_wal_stats = get_wal_stats()
    finally:
        set_synchronous_commit('on')

    return {
        "time_sec": round(end_time - start_time, 2),
        "wal_written": get_wal_diff(start_lsn, end_lsn),
        "ini_db_size": start_db_size,
        "db_size": end_db_size,
        **delta_wal_stats(start=start_wal_stats, end=end_wal_stats)
    }

def run_case_b():
    reset_wal_stats()
    try:
        set_synchronous_commit('off')
        start_time = time()
        start_lsn = get_wal_lsn()
        start_db_size = get_db_size()
        start_wal_stats = get_wal_stats()

        print("\nCASE B\n")
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
        end_wal_stats = get_wal_stats()
    finally:
        set_synchronous_commit('on')

    return {
        "time_sec": round(end_time - start_time, 2),
        "wal_written": get_wal_diff(start_lsn, end_lsn),
        "ini_db_size": start_db_size,
        "db_size": end_db_size,
        **delta_wal_stats(start=start_wal_stats, end=end_wal_stats)
    }

def run_case_c():
    abs_csv_path = os.path.abspath(CSV_FILE)
    reset_wal_stats()
    try:
        set_synchronous_commit('off')
        start_time = time()
        start_lsn = get_wal_lsn()
        start_db_size = get_db_size()
        start_wal_stats = get_wal_stats()

        print("\nCASE C: BULK COPY\n")
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
        end_wal_stats = get_wal_stats()
    finally:
        set_synchronous_commit('on')

    return {
        "time_sec": round(end_time - start_time, 2),
        "wal_written": get_wal_diff(start_lsn, end_lsn),
        "ini_db_size": start_db_size,
        "db_size": end_db_size,
        **delta_wal_stats(start=start_wal_stats, end=end_wal_stats)
    }

def cleanup():
    cursor.execute("""TRUNCATE TABLE trips RESTART IDENTITY;""")
    conn.commit()

## <--------------------    Enable WAL I/O timing     -------------------->
enable_wal_io_tracking()

## <--------------------    Run Cases     -------------------->
case_A_metrics = run_case_a()
print("\nCLEANUP\n")
cleanup()

case_B_metrics = run_case_b()
print("\nCLEANUP\n")
cleanup()

case_C_metrics = run_case_c()
print("\nCLEANUP\n")
cleanup()

print("\n=== CASE A: execute (x100k) + 1 Commit (synchronous_commit=off) ===")
print(case_A_metrics)
print("\n=== CASE B: [execute + commit](x100k) (synchronous_commit=off) ===")
print(case_B_metrics)
print("\n=== CASE C: BULK COPY (synchronous_commit=off) ===")
print(case_C_metrics)