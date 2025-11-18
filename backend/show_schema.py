import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

tables = ["mbo_data", "ohlc_candles", "absorption_events", "stops_icebergs"]

for table in tables:
    print("=" * 80)
    print(f"TABLE: {table}")
    print("=" * 80)

    # Get column information
    cursor.execute(
        """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """,
        (table,),
    )

    columns = cursor.fetchall()
    if columns:
        print(f"\nColumns ({len(columns)} total):")
        print(f"{'Column Name':<30} {'Type':<20} {'Nullable':<10} {'Default'}")
        print("-" * 80)
        for col_name, data_type, max_length, nullable, default in columns:
            type_str = data_type
            if max_length:
                type_str += f"({max_length})"
            default_str = str(default)[:30] if default else ""
            print(f"{col_name:<30} {type_str:<20} {nullable:<10} {default_str}")
    else:
        print("Table not found!")

    # Get row count
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"\nTotal Rows: {count:,}")
    except:
        pass

    # Get indexes
    cursor.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s
        ORDER BY indexname
    """,
        (table,),
    )

    indexes = cursor.fetchall()
    if indexes:
        print(f"\nIndexes ({len(indexes)} total):")
        for idx_name, idx_def in indexes:
            print(f"  - {idx_name}")

    # Get constraints
    cursor.execute(
        """
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = %s::regclass
        ORDER BY conname
    """,
        (table,),
    )

    constraints = cursor.fetchall()
    if constraints:
        print(f"\nConstraints ({len(constraints)} total):")
        for con_name, con_def in constraints:
            print(f"  - {con_name}: {con_def}")

    print()

cursor.close()
conn.close()
