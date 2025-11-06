#!/usr/bin/env python3
"""
Database Explorer - Check what data exists in TimescaleDB and Redis
"""

import redis
import psycopg2
from datetime import datetime

def explore_timescaledb():
    """Explore TimescaleDB tables and data"""
    print("\n" + "="*80)
    print("TIMESCALEDB EXPLORATION")
    print("="*80 + "\n")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='trading_data',
            user='postgres',
            password='X74Ot*BvtjgKuCBx'
        )
        cursor = conn.cursor()
        
        # List all tables
        print("📊 Available Tables:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table[0]}")
        
        print("\n" + "-"*80 + "\n")
        
        # For each table, show structure and sample data
        for table in tables:
            table_name = table[0]
            
            print(f"📋 Table: {table_name}")
            print("-" * 40)
            
            # Show columns
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print("   Columns:")
            for col in columns:
                print(f"      - {col[0]} ({col[1]})")
            
            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   Total Rows: {count:,}")
            
            # Show date range if timestamp column exists
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name IN ('timestamp', 'time', 'created_at')
            """)
            time_col = cursor.fetchone()
            
            if time_col and count > 0:
                time_col_name = time_col[0]
                cursor.execute(f"""
                    SELECT 
                        MIN({time_col_name}) as earliest,
                        MAX({time_col_name}) as latest
                    FROM {table_name}
                """)
                dates = cursor.fetchone()
                print(f"   Date Range: {dates[0]} to {dates[1]}")
            
            # Show sample data (first 3 rows)
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"   Sample Data (first {len(rows)} rows):")
                col_names = [desc[0] for desc in cursor.description]
                for row in rows:
                    print(f"      {dict(zip(col_names, row))}")
            
            print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error exploring TimescaleDB: {e}")

def explore_redis():
    """Explore Redis keys and data"""
    print("\n" + "="*80)
    print("REDIS EXPLORATION")
    print("="*80 + "\n")
    
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Get all keys (limit to 100 for safety)
        print("🔑 Redis Keys (sample):")
        keys = r.keys('*')
        print(f"   Total Keys: {len(keys)}")
        
        if len(keys) > 0:
            # Group keys by pattern
            patterns = {}
            for key in keys[:100]:  # Limit to first 100
                pattern = key.split(':')[0] if ':' in key else 'other'
                if pattern not in patterns:
                    patterns[pattern] = []
                patterns[pattern].append(key)
            
            print(f"\n   Key Patterns ({len(patterns)} types):")
            for pattern, pattern_keys in sorted(patterns.items()):
                print(f"      - {pattern}: {len(pattern_keys)} keys")
                # Show first 3 keys of this pattern
                for key in pattern_keys[:3]:
                    key_type = r.type(key)
                    if key_type == 'string':
                        value = r.get(key)
                        if len(str(value)) > 100:
                            value = str(value)[:100] + '...'
                        print(f"          {key} = {value}")
                    elif key_type == 'hash':
                        hash_data = r.hgetall(key)
                        print(f"          {key} (hash with {len(hash_data)} fields)")
                    elif key_type == 'list':
                        list_len = r.llen(key)
                        print(f"          {key} (list with {list_len} items)")
                    elif key_type == 'zset':
                        zset_len = r.zcard(key)
                        print(f"          {key} (sorted set with {zset_len} items)")
                    elif key_type == 'set':
                        set_len = r.scard(key)
                        print(f"          {key} (set with {set_len} items)")
        else:
            print("   ⚠️  No keys found in Redis")
        
        r.close()
        
    except Exception as e:
        print(f"❌ Error exploring Redis: {e}")

if __name__ == "__main__":
    explore_timescaledb()
    explore_redis()
    
    print("\n" + "="*80)
    print("EXPLORATION COMPLETE")
    print("="*80 + "\n")
