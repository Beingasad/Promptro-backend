import sys
import os
from sqlalchemy import create_engine, inspect

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SQLITE_URL = "sqlite:///../promptro.db"
NEON_URL = "postgresql://neondb_owner:npg_uOd34niXHloK@ep-patient-art-aqgw24bl.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

sqlite_engine = create_engine(SQLITE_URL)
neon_engine = create_engine(NEON_URL)

sqlite_inspector = inspect(sqlite_engine)
neon_inspector = inspect(neon_engine)

sqlite_tables = set(sqlite_inspector.get_table_names())
neon_tables = set(neon_inspector.get_table_names())

print("=== Comparing Database Tables ===")
print("Local SQLite Tables:", sorted(list(sqlite_tables)))
print("Production Neon Tables:", sorted(list(neon_tables)))

missing_tables_in_neon = sqlite_tables - neon_tables
extra_tables_in_neon = neon_tables - sqlite_tables

if missing_tables_in_neon:
    print(f"Missing tables in Neon: {missing_tables_in_neon}")
if extra_tables_in_neon:
    print(f"Extra tables in Neon: {extra_tables_in_neon}")

print("\n=== Comparing Table Columns ===")
common_tables = sqlite_tables.intersection(neon_tables)

for table in sorted(list(common_tables)):
    sqlite_cols = {col['name']: col['type'] for col in sqlite_inspector.get_columns(table)}
    neon_cols = {col['name']: col['type'] for col in neon_inspector.get_columns(table)}
    
    sqlite_colnames = set(sqlite_cols.keys())
    neon_colnames = set(neon_cols.keys())
    
    missing_cols = sqlite_colnames - neon_colnames
    extra_cols = neon_colnames - sqlite_colnames
    
    if missing_cols or extra_cols:
        print(f"Table: {table}")
        if missing_cols:
            print(f"  Missing columns in production (Neon): {missing_cols}")
            for col in missing_cols:
                print(f"    - Type in local SQLite: {sqlite_cols[col]}")
        if extra_cols:
            print(f"  Extra columns in production (Neon): {extra_cols}")
            for col in extra_cols:
                print(f"    - Type in Neon: {neon_cols[col]}")
