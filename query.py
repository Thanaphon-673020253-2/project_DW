import os
import duckdb

base_dir = os.path.dirname(os.path.abspath(__file__))

possible_paths = [
    os.path.join(base_dir, "indohotel", "dev.duckdb"),
    os.path.join(base_dir, "dev.duckdb")
]

db_path = next(
    (p for p in possible_paths if os.path.exists(p)),
    None
)

# Connect

conn = duckdb.connect(
    db_path,
    read_only=True
)

conn.execute("SET search_path = 'main';")


# รายชื่อตารางทั้งหมด
print("\n")
print("=" * 70)
print("ALL TABLES")
print("=" * 70)

tables_df = conn.execute("""
    SHOW TABLES
""").df()

print(tables_df.to_string(index=False))


#Select table that you want
print("="*70)
print("Table that you want na")
print("="*70)

df = conn.execute("""
    select * from main.stg_bookings

""").df()

print(df)
