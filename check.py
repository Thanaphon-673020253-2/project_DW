import os
import duckdb

# =========================================================
# หา dev.duckdb
# =========================================================
base_dir = os.path.dirname(os.path.abspath(__file__))

possible_paths = [
    os.path.join(base_dir, "indohotel", "dev.duckdb"),
    os.path.join(base_dir, "dev.duckdb")
]

db_path = next(
    (p for p in possible_paths if os.path.exists(p)),
    None
)

if not db_path:
    print("❌ ไม่พบไฟล์ dev.duckdb")
    print("ตรวจสอบ path แล้ว:")
    for p in possible_paths:
        print(" -", p)
    raise SystemExit

print("=" * 70)
print("DATABASE FOUND")
print("=" * 70)
print(db_path)


# =========================================================
# Connect
# =========================================================
conn = duckdb.connect(
    db_path,
    read_only=True
)

conn.execute("SET search_path = 'main';")


# =========================================================
# 1. รายชื่อตารางทั้งหมด
# =========================================================
print("\n")
print("=" * 70)
print("1. ALL TABLES")
print("=" * 70)

tables_df = conn.execute("""
    SHOW TABLES
""").df()

print(tables_df.to_string(index=False))


# =========================================================
# 2. รายละเอียดทุกตาราง
# =========================================================
print("\n")
print("=" * 70)
print("2. TABLE STRUCTURE")
print("=" * 70)

for table in tables_df["name"]:

    print("\n")
    print("-" * 70)
    print(f"TABLE: {table}")
    print("-" * 70)

    try:

        columns_df = conn.execute(
            f'DESCRIBE main."{table}"'
        ).df()

        print(
            columns_df[
                ["column_name", "column_type"]
            ].to_string(index=False)
        )

    except Exception as e:

        print("❌ ไม่สามารถอ่านตาราง:", e)
conn.close()