import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

print("=" * 80)
print("DATABASE INSPECTION - ALL TABLES")
print("=" * 80)

# Get all tables
cur.execute(
    """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name
"""
)
tables = [row[0] for row in cur.fetchall()]

print(f"\nFound {len(tables)} tables: {', '.join(tables)}")
print()

for table in tables:
    print("=" * 80)
    print(f"TABLE: {table}")
    print("=" * 80)

    # Get column info
    cur.execute(
        f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
    """
    )
    columns = cur.fetchall()

    print("\nCOLUMNS:")
    for col in columns:
        nullable = "NULL" if col[2] == "YES" else "NOT NULL"
        print(f"  {col[0]:<25} {col[1]:<25} {nullable}")

    # Get row count
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"\nTOTAL ROWS: {count:,}")

    if count > 0:
        # Get date range if timestamp column exists
        if any(col[0] == "timestamp" for col in columns):
            cur.execute(
                f"""
                SELECT 
                    MIN(timestamp AT TIME ZONE 'America/New_York') as first_ts,
                    MAX(timestamp AT TIME ZONE 'America/New_York') as last_ts
                FROM {table}
            """
            )
            date_range = cur.fetchone()
            print(f"DATE RANGE: {date_range[0]} to {date_range[1]}")

        # Get distinct symbols if symbol column exists
        if any(col[0] == "symbol" for col in columns):
            cur.execute(
                f"""
                SELECT DISTINCT symbol, COUNT(*) as cnt
                FROM {table}
                GROUP BY symbol
                ORDER BY cnt DESC
                LIMIT 5
            """
            )
            symbols = cur.fetchall()
            print("\nTOP SYMBOLS:")
            for sym in symbols:
                print(f"  {sym[0]:<30} {sym[1]:>10,} rows")

        # Get CBDR window breakdown if cbdr_window column exists
        if any(col[0] == "cbdr_window" for col in columns):
            cur.execute(
                f"""
                SELECT cbdr_window, COUNT(*) as cnt
                FROM {table}
                GROUP BY cbdr_window
                ORDER BY cnt DESC
            """
            )
            cbdr = cur.fetchall()
            print("\nCBDR WINDOW BREAKDOWN:")
            for window in cbdr:
                window_name = window[0] if window[0] else "NULL"
                print(f"  {window_name:<20} {window[1]:>10,} rows")

        # Show sample rows
        print("\nSAMPLE ROWS (first 3):")
        cur.execute(f"SELECT * FROM {table} LIMIT 3")
        samples = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

        for i, sample in enumerate(samples, 1):
            print(f"\n  Row {i}:")
            for col_name, value in zip(col_names, sample):
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 60:
                    str_value = str_value[:57] + "..."
                print(f"    {col_name:<20} = {str_value}")

    print()

print("=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)

cur.close()
conn.close()
