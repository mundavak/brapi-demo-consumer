"""
Database Schema Discovery - Complete inventory of all tables and data
"""

import psycopg2
from datetime import datetime
import pytz
import json

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

est = pytz.timezone("America/New_York")

print("=" * 80)
print("COMPLETE DATABASE SCHEMA DISCOVERY")
print("=" * 80)
print()

cur = conn.cursor()

# 1. List all tables in the database
print("1. ALL TABLES IN DATABASE:")
print("-" * 80)

cur.execute(
    """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
"""
)

tables = cur.fetchall()
table_list = [t[0] for t in tables]

print(f"Found {len(table_list)} tables:\n")
for table in table_list:
    print(f"  - {table}")

# 2. For each table, get schema and row count
print("\n" + "=" * 80)
print("2. DETAILED TABLE SCHEMAS:")
print("=" * 80)

schema_inventory = {}

for table in table_list:
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table}")
    print("-" * 80)

    # Get column definitions
    cur.execute(
        """
        SELECT 
            column_name, 
            data_type, 
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' 
          AND table_name = %s
        ORDER BY ordinal_position
    """,
        (table,),
    )

    columns = cur.fetchall()

    # Get row count
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cur.fetchone()[0]
    except:
        row_count = 0

    # Get primary keys
    cur.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
    """,
        (table,),
    )

    primary_keys = [row[0] for row in cur.fetchall()]

    # Get indexes
    cur.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s AND schemaname = 'public'
    """,
        (table,),
    )

    indexes = cur.fetchall()

    print(f"Row Count: {row_count:,}")
    print(f"Primary Keys: {', '.join(primary_keys) if primary_keys else 'None'}")
    print(f"\nColumns:")

    column_defs = []
    for col_name, data_type, max_length, nullable, default in columns:
        type_str = data_type
        if max_length:
            type_str += f"({max_length})"
        null_str = "NULL" if nullable == "YES" else "NOT NULL"
        default_str = f" DEFAULT {default}" if default else ""
        print(f"  - {col_name:30s} {type_str:30s} {null_str}{default_str}")

        column_defs.append(
            {
                "name": col_name,
                "type": type_str,
                "nullable": nullable == "YES",
                "default": default,
            }
        )

    if indexes:
        print(f"\nIndexes ({len(indexes)}):")
        for idx_name, idx_def in indexes:
            print(f"  - {idx_name}")

    # Store in inventory
    schema_inventory[table] = {
        "row_count": row_count,
        "columns": column_defs,
        "primary_keys": primary_keys,
        "indexes": [idx[0] for idx in indexes],
    }

# 3. Check for trades and depth data specifically
print("\n" + "=" * 80)
print("3. SEARCHING FOR TRADES AND DEPTH DATA:")
print("=" * 80)

trades_tables = [t for t in table_list if "trade" in t.lower()]
depth_tables = [t for t in table_list if "depth" in t.lower() or "book" in t.lower()]

print(f"\nTrades-related tables: {trades_tables if trades_tables else 'None found'}")
print(f"Depth-related tables: {depth_tables if depth_tables else 'None found'}")

# Check if there's data with "trade" or "depth" in any table
print("\nSearching for trade/depth related data in existing tables...")

# Check stops_icebergs for any trade-related info
if "stops_icebergs" in table_list:
    print("\n  Checking stops_icebergs table...")
    cur.execute(
        """
        SELECT DISTINCT event_type 
        FROM stops_icebergs 
        ORDER BY event_type
    """
    )
    event_types = [r[0] for r in cur.fetchall()]
    print(f"    Event types: {', '.join(event_types)}")

# 4. Check Nov 6 data availability for each table
print("\n" + "=" * 80)
print("4. NOV 6, 2025 DATA AVAILABILITY:")
print("=" * 80)

nov6_data = {}

for table in table_list:
    try:
        # Try to find timestamp column
        cur.execute(
            f"""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = %s 
              AND (data_type = 'timestamp with time zone' OR column_name = 'timestamp')
            LIMIT 1
        """,
            (table,),
        )

        ts_col = cur.fetchone()
        if ts_col:
            ts_col_name = ts_col[0]

            # Get Nov 6 data range
            cur.execute(
                f"""
                SELECT 
                    COUNT(*) as count,
                    MIN({ts_col_name}) as earliest,
                    MAX({ts_col_name}) as latest
                FROM {table}
                WHERE {ts_col_name} >= '2025-11-06 00:00:00-05:00'
                  AND {ts_col_name} < '2025-11-07 00:00:00-05:00'
            """
            )

            result = cur.fetchone()
            count, earliest, latest = result

            if count and count > 0:
                print(f"\n{table}:")
                print(f"  Records: {count:,}")
                print(
                    f"  Range: {earliest.strftime('%H:%M:%S')} - {latest.strftime('%H:%M:%S')} EST"
                )

                nov6_data[table] = {
                    "count": count,
                    "earliest": str(earliest),
                    "latest": str(latest),
                }
    except Exception as e:
        pass

# 5. Create comprehensive summary
print("\n" + "=" * 80)
print("5. SUMMARY FOR AI MEMORY:")
print("=" * 80)

summary = {
    "database": "trading_data",
    "host": "localhost:5432",
    "discovered_date": "2025-11-06",
    "total_tables": len(table_list),
    "tables": schema_inventory,
    "nov6_data_availability": nov6_data,
    "notes": {
        "mbo_data_cutoff": "2025-11-06 09:29:59 EST (stops before NY session)",
        "trades_tables_found": trades_tables,
        "depth_tables_found": depth_tables,
        "primary_data_sources": [
            "stops_icebergs (stop hunts and iceberg orders)",
            "mbo_data (market-by-order data, but limited hours)",
            "ohlc_candles (OHLC candle data)",
            "absorption_events (absorption indicator events)",
        ],
    },
}

print("\nKey Findings:")
print(f"  - Total tables: {len(table_list)}")
print(f"  - Tables with Nov 6 data: {len(nov6_data)}")
print(f"  - Trades tables: {len(trades_tables)}")
print(f"  - Depth tables: {len(depth_tables)}")

# Save to JSON file
output_file = "database_schema_inventory.json"
with open(output_file, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n✅ Complete schema saved to: {output_file}")
print("=" * 80)

cur.close()
conn.close()
