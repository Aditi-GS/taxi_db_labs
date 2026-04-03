## Table Of Contents:
0. [Week 1 Objectives](#objectives)
1. [Compare Insertion Methods](#part-1)  
2. [WAL Deep Dive](#part-2)
3. [WAL Deep Dive](#part-3)
4. [WAL Deep Dive](#part-4)
5. [WAL Deep Dive](#part-5)
6. [WAL Deep Dive](#part-6)

---

## Objectives  
Understand how PostgreSQL handles writes internally - WAL, transactions, commit strategies, and partitioning.  

1. Test **Batch Insert** vs **Row-by-Row Insert** vs **Bulk Streaming**  
2. WAL Deep Dive  
3. Indexes and Write Slowdown  
4. Load Full Dataset (~30–50M rows)  
5. `synchronous_commit` Tradeoff  
6. Partitioning by Time  

---

## Part 1
<details>
    <summary>Compare Insertion Methods</summary>

#### GOAL: Batch Insert VS Row-by-Row Insert VS Bulk COPY  

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

> WAL records are stored as sequential, append-only segment files in the `pg_wal` directory (or `pg_xlog` in versions prior to PostgreSQL 10). By default, each WAL segment file (pre-allocated segment) is 16 MB in size, though this can be configured during cluster initialization. These files have 24-character hexadecimal names.  

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

---> returns the current WAL LSN (Log Sequence Number) - essentially the "position" of WAL writes at that moment
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
`fsync = file sync = system call to flush everything in the memory for the file to the disk [happens at commit()]`  
`fsync = durability`   
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
</details>

---

## Part 2
<details>
<summary>WAL Deep Dive</summary>
<br>

Earlier we mentioned PostgreSQL actually treats every SQL statement as being executed within a transaction - BUT this is ONLY if autocommit = ON.  
For psycopg2 default = autocommit OFF.  
```python
# subset = 100k rows
for idx, row in subset.iterrows():
    cursor.execute(...)
conn.commit()
```  
Here, execution happens 100k times BUT commit only happens once.  
So in PART 1:  
CASE A
```
execute 100k times => SQL Parsing
commit once => Transaction (containing 100,000 inserts)
```  
This is not the same as:  
CASE B
```
execute
commit
execute
commit
... (x100k)
```  

Now - for CASE B:  
- 100k transaction begin/commit records in WAL
- 100k fsync operations
- 100k durability guarantees

CASE A and B both make 100k network calls/round trips => both make 100k `execute()` calls => CASE B inclues 100k `commit()` calls with it but CASE A makes only 1 at the end.

> COPY avoids  
- network round trips
- per-row SQL parsing + planning
- per-row executor overhead

**_NOTE_** : So in the calculations made in PART 1, we are NOT accounting for all the latencies - that is - latencies caused by Python, Network calls/round trips (Client <-> Server), PostgreSQL execution, Disk (WAL + data).  
> Bulk vs row -> CPU + network + transaction + WAL + parsing  
> `fsync` calls are expensive => Disk I/O is slow.  
> CPU + I/O overhead dominates time  

---

***`TRANSACTION LIFECYCLE`***  
1. **Active State**
    - Modifications made in memory (buffers)
2. **Partially Commited state**
    - Last statement executed successfully -> preparing to make changes permanent
3. **Commited State**
    - Transaction completed successfully -> changes made DURABLE
4. **Failed State**
5. **Aborted/Roll Back State**
6. **Terminated State**
    - Final consistent state post commit or rollback => All resources released (locks, memory,...)  

![1775068278820](image/README/1775068278820.png)

---

Now let's consider 3 cases instead of 2:
1. Execute + Commit per Row = Worst Case  
2. Execute x100k + Commit Once (Batch) = from Part 1
3. COPY = from part 1

---

> Beyond Just SQL Statement Parsing:  

`SQL parse + plan (happens per statement)`  
- Target table/index pages are located (or loaded) into **shared buffers (PostgreSQL RAM)**  

`Executor overhead (per row)`  
- PostgreSQL evaluates each row, checks types, enforces constraints  
- Corresponding data page is modified in **shared buffers**
- Data Page become **dirty** => not yet persisted on disk  

`WAL Record Generation`  
- PostgreSQL creates a WAL record describing the change  
- Appends it to **WAL buffers (in shared memory = PostgreSQL RAM)**  
- Each WAL record gets a **LSN (Log Sequence Number)**  
- Each modified data page is tagged with that LSN  

__IMPORTANT__: A data page cannot be written to disk unless its WAL (up to that LSN) is persisted

`WAL write + flush (durability boundary)`  
```
    WAL Buffers (PostgreSQL RAM)
                |
            `write()`
                |
    OS Page Cache (Kernel RAM)
                |
            `fsync()`
                |
            Disk (Persistent)
```  

`Data file writes (asynchronous)`  
- Dirty data pages are flushed later by:  
  - background writer  
  - checkpointer  
- Data files may lag behind WAL  
- WAL is the **source of truth for recovery**  



`Network round trips (per execute/commit)`
- every `execute()` (sent by client) involves sending the query + receiving ack/result (sent by server)  

`Client-side Python overhead`  
- iteration, tuple conversion, logging  

> Durability is acheived by persisting the WAL Record - not when the data page is persisted.

**Per-row executor overhead**  
= all the internal work PostgreSQL does to execute a statement for a single row  
= expression evaluation >> data type checks >> constraint checks >> tuple formation >> buffer/page updates >> WAL generation
**Protocol overhead**  
= extra bytes + processing to wrap query/results in PostgreSQL's wire protocol  
= framing/decoding/metadata per message

---
> Major changes from Part 1 to highlight:
- Clearly mention the latencies which are unaccounted for
- WAL size is the wrong metric to check performance of ROW-WISE INSERTION & BULK COPY
---

Depending on your application and objective, you will need to always decide between `speed` or `durability`

### New Metrics  
1. `wal_buffers_full`  
- Number of times WAL buffers filled up -> forcing a flush to OS Page Cache  
- Indicates memory pressure on WAL buffers  
2. `wal_write`  
- Number of `write()` system calls made from WAL buffers to OS Page Cache  
- wal_write can happen even if there is space in WAL buffer - i.e, - they don't necessarily happen only when buffers are full (e.g: commit of a transaction / checkpoint)    
3. `wal_write_time`  
- Time taken to move WAL from Postgres RAM to Kernel/OS RAM  
4. `wal_sync`  
- Number of `fsync()` calls made to flush WAL from Kernel Cache to Disk  
- Critical for durability  
5. `wal_sync_time`  
- Total time spent in fsync() calls  
- Reflects the durable I/O overhead  

> **Checkpoint**: critical internal process which:  
- writes ***dirty pages*** to disk  
- marks a specific LSN -- all WAL up to this point can be considered safe  

So it:  
- reduces recovery time after a crash (PostgreSQL only needs to replay WAL after the last checkpoint)  
- allows WAL files to be recycled (prevents the WAL directory from growing indefinitely)

When it is triggered:  
- Every `checkpoint_timeout` seconds  
- When `max_wal_size` is reached  
- Manually  
- Forced, during server shutdown  

```sql
-- enable wal I/O time tracking + reload the config
-- make sure to set autocommit = true 
ALTER SYSTEM SET track_wal_io_timing = on;
SELECT pg_reload_conf();
-- sys function resets the statistics counters for write-ahead logging (WAL)
SELECT pg_stat_reset_shared('wal');
```

Commands like `ALTER SYSTEM` affect the whole system or shared memory, so PostgreSQL requires them to run outside any transaction block and since Postgres treats every DDL statement as a transaction by default, for such commands, `autocommit` should be enabled. Other examples include `CREATE DATABASE`, `VACCUM FULL`, etc.  

### Results
```
=== CASE A: execute (x100k)  + 1 Commit ===
{'time_sec': 40.8, 'wal_written': '27 MB', 'ini_db_size': '8582 kB', 'db_size': '28 MB', 'wal_buffers_full': 0, 'wal_write': Decimal('197'), 'wal_write_bytes': Decimal('27860992'), 'wal_write_time_ms': 581.06, 'wal_sync': Decimal('0'), 'wal_sync_time_ms': 0.0}

=== CASE B: [execute + commit](x100k) ===
{'time_sec': 75.05, 'wal_written': '62 MB', 'ini_db_size': '8582 kB', 'db_size': '28 MB', 'wal_buffers_full': 0, 'wal_write': Decimal('99927'), 'wal_write_bytes': Decimal('915652608'), 'wal_write_time_ms': 15086.47, 'wal_sync': Decimal('2'), 'wal_sync_time_ms': 88.04}

=== CASE C: BULK COPY (Streaming) ===
{'time_sec': 4.5, 'wal_written': '22 MB', 'ini_db_size': '8590 kB', 'db_size': '28 MB', 'wal_buffers_full': 2317, 'wal_write': Decimal('2418'), 'wal_write_bytes': Decimal('40828928'), 'wal_write_time_ms': 314.58, 'wal_sync': Decimal('1'), 'wal_sync_time_ms': 58.9}
```

---

### Why is `wal_sync = 0` for Case A? (Deferred fsync confusion)

#### Assumption
From the assumptions made about the results based on mental theoritical model: `fsync = durability` and Case B has 100k commits => 100k fsync operations.  
So Case A should have at least **1 fsync** at its single `commit()`.  
Seeing `wal_sync = 0` for Case A looks like a durability gap - as if the committed data was never flushed to disk.

#### Actual Result

| | Case A | Case B | Case C |
|---|---|---|---|
| Transactions | 1 | 100,000 | 1 |
| fsyncs needed | 1 | 100,000 | 1 |
| `wal_sync` observed | **0** | 2 | 1 |
| Durable? | **Yes** | Yes | Yes |

Case B's `wal_sync = 2` is also surprising - 100k commits reduced to just 2 fsyncs.

#### Why it happened

**Case A - `wal_sync = 0`**

`wal_sync` in `pg_stat_io` (PG18) is scoped per `backend_type`. The view tracks fsyncs by the process that issued the `fsync()` syscall - but that process is not always the client session. PostgreSQL has a dedicated **WAL writer background process** (`walwriter`) whose job is to flush WAL to disk periodically and at commit. When the client session commits, it signals the WAL writer, which performs the actual `fsync()`. That call is attributed to the `walwriter` backend type row - not `client backend`.

Since `pg_stat_reset_shared('io')` resets all backend types together, and the measurement window captures what happened *during* the test, the timing matters: if `walwriter` issued its fsync slightly after `end_wal_stats` was captured, the count lands outside the measurement window entirely.

```
Client session (python code) --> commit() --> signals WAL writer --> walwriter process --> fsync() [attributed here, not to client backend]
```

To see it:
```sql
SELECT backend_type, fsyncs, fsync_time
FROM pg_stat_io
WHERE object = 'wal' AND fsyncs > 0;
```
Results:  
```
"backend_type"	"fsyncs"	"fsync_time"
"client backend"	1	58.902
```

**Case B - `wal_sync = 2` instead of 100,000**

PostgreSQL's **group commit** optimization batches multiple concurrent commits into a single fsync. When 100k commits arrive in rapid succession (as in a tight Python loop), the WAL writer groups them and issues one fsync covering all pending WAL records up to the latest LSN. This is `synchronous_commit = on` with group commit doing its job - every transaction still waits for its WAL to be on disk before `commit()` returns, but the actual `fsync()` syscall is shared across the group.

**Case C - `wal_sync = 1`**

COPY is a single transaction. One commit, one fsync. Straightforward. `wal_buffers_full = 2317` shows the WAL buffer filled and was flushed to OS page cache 2317 times mid-stream (these are `write()` calls, not `fsync()` calls - the data was in kernel RAM but not yet on disk). The single fsync at commit made all of it durable in one shot.

#### The corrected mental model

`wal_sync = 0` does **not** mean "not durable". It means the fsync was issued by a background process (`walwriter`), not by the client session directly, and/or landed outside the measurement window.

```
WAL Buffers (PostgreSQL RAM)
            |
        write()   <-- wal_write: attributed to whoever called write()
            |             (could be client backend OR walwriter)
OS Page Cache (Kernel RAM)
            |
        fsync()   <-- wal_sync: attributed to whoever called fsync()
            |             (almost always walwriter, not client backend)
        Disk (Persistent)
```

`wal_write` and `wal_sync` measure **who did the syscall**, not **who triggered it**.

#### Conclusion

- `wal_sync = 0` for Case A is a **measurement attribution artifact**, not a durability gap. The data is durable - the WAL writer performed the fsync on behalf of the committing session.
- `wal_sync = 2` for Case B confirms **group commit** is real and highly effective - 100k logical durability guarantees collapsed into 2 physical fsync calls.
- `wal_sync` as a metric is most useful for understanding **fsync pressure on the WAL writer process**, not for counting per-transaction durability events. For the latter, `wal_write` (write to OS page cache) is the more reliable counter within a measurement window.
- To get a complete picture, always query `pg_stat_io` broken down by `backend_type` - aggregating across all types (as `get_wal_stats()` does) is correct for totals but hides *who* is doing the I/O work.

> **__NOTE__**  
**`walwriter`**  
PostgreSQL has a dedicated background worker - the WAL writer - whose only job is to sit in a loop and flush WAL to disk. Your session posts a request and waits for the WAL writer to confirm it's done.  
**`pg_stat_io`** tracks I/O activity for each type of process separately. `backend_type` is the role indicator here.  


| Process | Role | backend_type |
|---|---|---|
| Our Python Code | Takes orders, runs queries | client backend |
| WAL Writer | Only job: flush WAL to disk | walwriter |
| Background Writer | Flushes dirty data pages | background writer |
| Checkpointer | Periodic full flush to disk | checkpointer |  

Our current get_wal_stats() uses SUM(fsyncs) across all backend_type rows - which - idealistically capture everything.  
BUT:  
The WAL writer is an independent process - it doesn't fsync the moment you commit.  
There's a small delay (walwriter wakes up -> calls fsync() for us -> records fsyncs += 1).  
If our end_wal_stats snapshot is taken before the WAL writer finishes, the fsync lands outside your measurement window.  
***One way to bypass the issue of recording the stats outside the measurement window is to add sleep time.***  
**`Group Commit`**  
Postgres knows fsync is expensive - in order to avoid the obvious fsync delays - it performs group commit.  
This happens when multiple concurrent commits arrive faster than the WAL writer can process them.  
It automatically batches multiple concurrent commits into one fsync, which is why Case B shows 2 fsyncs not 100k. But we still can see that the  `wal_write_bytes` was `915652608` despite `wal_written` (based on LSN diff) is `62MB`. It's because even if group commit was performed as an optimization for `fsync()` calls - every individual `write()` syscall carried its own small WAL record with transaction metadata, per-call rather than per-batch => they weren't grouped.  

The approach in PART 1.1 might make up for the unaccounted metrics in PART 1, but it doesn't account for the internal processes handled within Postgres, with the assumption that all activities are initiated and tracked for our Python session only.

</details>

---

## Part 3
<details>
<summary></summary>
<br>


</details>

---

## Part 4
<details>
<summary></summary>
<br>


</details>

---

## Part 5
<details>
<summary></summary>
<br>


</details>

---

## Part 6
<details>
<summary></summary>
<br>


</details>

---