## Table Of Contents:
0. [Overview](#overview)
1. [Write-Heavy Workload](#part-1)

## Overview
***Dataset*** = NYC Taxi dataset  
***Link*** = https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

***About the dataset***  
Yellow and green taxi trip records include fields capturing pickup and drop-off dates/times, pickup and drop-off locations, trip distances, itemized fares, rate types, payment types, and driver-reported passenger counts.  
For-Hire Vehicle (“FHV”) trip records include fields capturing the dispatching base license number and the pickup date, time, and taxi zone location ID. 
All raw trip data is stored in Parquet file type.  
Parquet is the industry standard for working with big data. Using Parquet format
results in reduced file sizes and increased speeds. 

## Part 1
> Load `NYC Taxi dataset` (~30–50M rows)  
> Test **bulk insert** vs **row-by-row insert** vs **
> Measure `WAL` growth & insert `latency`  
> Add `basic indexes` and observe insertion slowdown  

---  
1. **Write-Ahead Logging (WAL)**:
- Sequential record of all changes made to a database
- Mechanism used to ensure data durability, consistency, and recovery in the event of failures 
- Upon transactions, changes are first appended to the WAL file before they are applied to the actual on-disk table data files  (where tables and indexes reside)  
- Enables Point-In-Time Recovery AND Roll-Forward Recovery (also known as REDO)  
- Reduces disk I/O overhead by allowing sequential writes to the log rather than random writes to data files  
---  

2. **Indexes**:
- Similar to *table of contents* for your database
- Specialized data structures (such as B-Trees, Hash indexes, or LSM trees) designed to speed up data retrieval by allowing the database to locate specific rows without scanning the entire table
- Significantly increases read performance
---  

- Yellow Taxi Trip Records : June 2025  
- Parquet <-> CSV   
Though Parquet is optimal choice for big data, Postgres can't load it directly - it loads data row-by-row, which is easier when it is CSV format.  
- Sequential inserts:  
&#9744; No concurrency issues => no deadlocks or transaction conflicts  
&#9744; WAL writing overhead for every insert  
---  

> Data files consist of fixed-size pages (typically 8 kB) that store tables and indexes as arrays of these pages on disk. These files are stored in the database's data directory (often `$PGDATA`).  
8 kB pages structured with a `PageHeaderData` (24 bytes), an array of line pointers (ItemIdData), free space, and heap tuples stored backward from the end.  The `pd_lower` and `pd_upper` fields track free space boundaries. Special space is used by indexes.  

> WAL records are stored as sequential, append-only segment files in the `pg_wal` directory (or `pg_xlog` in versions prior to PostgreSQL 10). By default, each WAL segment file is 16 MB in size, though this can be configured during cluster initialization. These files have 24-character hexadecimal names.  

To Examine:  
**Data pages**: Use the `pageinspect` extension (page_header(), heap_page_items()).  
```sql
CREATE EXTENSION pageinspect;
SELECT * FROM page_header(get_raw_page('<table_name>', 0));
SELECT * FROM heap_page_items(get_raw_page('<table_name>', 0));
```  
**WAL segments**: Use pg_waldump or pg_walinspect.inspect_wal()  
```sql
CREATE EXTENSION pg_walinspect;
SELECT * FROM pg_get_wal_records_info('start_lsn', 'end_lsn');
SELECT * FROM pg_get_wal_stats('start_lsn', 'end_lsn');
```
---
### Metrics:  
1. Insert Time  
2. WAL Growth  
3. DB Size  
---
> To check **WAL growth**:  
```sql
SELECT pg_current_wal_lsn(); 

---> returns the current WAL LSN (Log Sequence Number) — essentially the "position" of WAL writes at that moment
```
OR 
```sql
SELECT pg_size_pretty(
    pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')
) AS wal_written;

---> pg_wal_lsn_diff(lsn1, lsn2) calculates the difference in bytes between two LSNs
---> '0/0' is the very start of WAL (since the start of the server)
---> total WAL written = pg_size_pretty() converts the raw byte difference into a human-readable format (e.g., MB, GB)
```  
---
**`Transaction`** is that it bundles multiple steps into a single, all-or-nothing operation.  
When multiple transactions are running concurrently, each one should not be able to see the incomplete changes made by others.  
PostgreSQL actually treats every SQL statement as being executed within a transaction.  

> **Then in such case, due to isolation (AC`I`D), what if Transaction A and B are running concurrently. What if the changes in Transaction B affects the result of Transaction A ? In that case, won't that return stale/old result ?**  
Example:  
Transaction A: Totals the balances in a branch.   
Transaction B: Transfers money between accounts, which changes balances in that branch.  

Databases allow different levels of isolation:  
1. Read Uncommited -> B can see the uncommited changes of A -> can lead to Dirty Reads (wrong values)  
2. Read Commited -> A waits for B to commit changes -> A waits or uses old values  
3. Serializable -> db may block Transaction B until Transaction A finishes  
---
> **What's the difference between BATCH INSERT and BULK COPY?**  

`BATCH INSERT`   
- Client-side Streaming  
- Client can control how many rows to insert per batch  
- Client memory usage matters if batch is very big  
- Batch insert still generates WAL per row in terms of row-level info, but fewer fsyncs or transaction overhead compared to row-by-row  
`fsync = file sync = system call to flush everything in the memory for the file to the disk.`  
Every transaction requires the DB to:  
1. Track changes in memory  
2. Write changes to WAL  
3. Ensure atomicity (commit or rollback)  

> Transaction Overhead = Logging transaction begin/commit in WAL + Lock management for concurrent access + Metadata management for rollback and MVCC  

`BULK COPY`   
- Server-side Streaming  
- Data File is streamed directly into Postgres internally 
- Minimal client CPU/memory usage  
- WAL is written efficiently in large sequential chunks (contiguous on disk), not per row
---

### Results:
> ROW WISE INSERTION (100K rows):
Time Taken = 34.02s  
WAL Written = 27 MB  

> BULK COPY (100k rows):
Time Taken = 4.11s  
WAL Written = 22 MB  

For 100k rows, we can clearly see that time taken for bulk copy is almost `~8.5x` faster.  
The WAL written size is not significantly less for bulk copy. 

Now let us imagine there are ~50M rows, then an idealistic estimate would be: 
> ROW WISE INSERTION (50,000k rows):  
Time Taken = 34.02s x 500 = 17010 ≈ 4.7 hours  
WAL Written = 27 MB x 500 ~ 13.5 GB  

> BULK COPY (50,000k rows):  
Time Taken = 4.11s x 500 = 2055 s ≈ 34 minutes  
WAL Written = 22 MB x 500 ~ 11 GB  

So loading ~50M records will take idealistically ~3 mins compared to ~30 mins.  
Now coming to the WAL size, it doesn't shrink as much because PostgreSQL still logs all the data changes (as it should)
but fewer statement-level WAL writes are executed in case of BULK COPY - reducing the overhead.