## Table Of Contents:
0. [Overview](#overview)
1. [Write-Heavy Workload](#week-1)

---

## Overview

***Dataset*** = NYC Taxi dataset [Yellow Taxi 2025-26] = yellow_tripdata_2025-06.parquet  
***Link*** = https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page  
***Data Dictionary*** = data_dictionary_trip_records_yellow.pdf

***About the dataset***  
Yellow and green taxi trip records include fields capturing pickup and drop-off dates/times, pickup and drop-off locations (Taxi Zone Lookup), trip distances, itemized fares, rate types, payment types, and driver-reported passenger counts.  
For-Hire Vehicle ("FHV") trip records include fields capturing the dispatching base license number and the pickup date, time, and taxi zone location ID.  
All raw trip data is stored in Parquet file type.  
Parquet is the industry standard for working with big data. Using Parquet format
results in reduced file sizes and increased speeds.  

---

## Week 1  
#### Goal:  
Understand how PostgreSQL handles writes internally - WAL, transactions, commit strategies, and partitioning.  

1. Test **Batch Insert** vs **Row-by-Row Insert** vs **Bulk Streaming**  
2. WAL Deep Dive  
3. Indexes and Write Slowdown  
4. Load Full Dataset (~30–50M rows)  
5. `synchronous_commit` Tradeoff  
6. Partitioning by Time  

---

