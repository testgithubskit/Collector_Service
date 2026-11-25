import pandas as pd
import pyodbc

file_path = r"G:\GOKUL\TOYOTA\Collector_1\DATA.xlsx"

# 🔥 Fix header issue
df = pd.read_excel(file_path, engine="openpyxl", header=1)

# Clean column names
df.columns = df.columns.str.strip().str.lower()

print(df.columns)  # debug

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Machine_DB;"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO MCT_Data 
        (machine_number, timestamp_timezone, cycle_time, model, counter)
        VALUES (?, ?, ?, ?, ?)
    """,
        row["machine_number"],
        row["timestamp_timezone"],
        float(row["cycle_time"]),
        int(row["model"]),
        int(row["counter"])
    )

conn.commit()
cursor.close()
conn.close()

print("✅ Data inserted successfully!")