"""
Quick database connection test
Run this directly on production server
"""
import psycopg2
import sys

print("="*60)
print("  Testing Database Connection Configurations")
print("="*60)

configs = [
    {'host': 'localhost', 'port': '5433', 'password': 'postgres', 'label': 'Current config'},
    {'host': 'localhost', 'port': '5432', 'password': 'postgres', 'label': 'Default port'},
    {'host': 'localhost', 'port': '5433', 'password': 'postgres123', 'label': 'Alt password'},
    {'host': '127.0.0.1', 'port': '5433', 'password': 'postgres', 'label': 'IP address'},
]

success = False
for i, cfg in enumerate(configs, 1):
    try:
        print(f"\n[Test {i}] {cfg['label']}")
        print(f"  host={cfg['host']}, port={cfg['port']}, password={cfg['password']}")
        
        conn = psycopg2.connect(
            host=cfg['host'],
            port=cfg['port'],
            database='nanovna_db',
            user='postgres',
            password=cfg['password'],
            connect_timeout=3
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_database()")
        version, db = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"  [SUCCESS] Connected to database '{db}'!")
        print(f"  PostgreSQL: {version[:60]}...")
        print(f"\n" + "="*60)
        print("  UPDATE app.py DB_CONFIG with:")
        print("="*60)
        print(f"  'host': '{cfg['host']}',")
        print(f"  'port': '{cfg['port']}',")
        print(f"  'password': '{cfg['password']}'")
        print("="*60)
        
        success = True
        break
        
    except Exception as e:
        print(f"  [FAILED] {type(e).__name__}: {e}")

if not success:
    print("\n" + "="*60)
    print("  ALL CONNECTION ATTEMPTS FAILED!")
    print("="*60)
    print("\nPlease check:")
    print("  1. PostgreSQL service is running")
    print("  2. Database 'nanovna_db' exists")
    print("  3. Password is correct")
    print("  4. Port is not blocked by firewall")
    sys.exit(1)
else:
    sys.exit(0)
