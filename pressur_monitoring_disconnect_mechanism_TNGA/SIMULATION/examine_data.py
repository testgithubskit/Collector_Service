import pandas as pd

file_path = r"G:\GOKUL\TOYOTA\Collector_1\DATA.xlsx"

# Read Excel data
df = pd.read_excel(file_path, engine="openpyxl", header=1)
df.columns = df.columns.str.strip().str.lower()

print("Columns:", df.columns.tolist())
print(f"Total rows: {len(df)}")
print("\nFirst 10 rows:")
print(df.head(10).to_string())

# Convert timestamp to datetime
df['timestamp_timezone'] = pd.to_datetime(df['timestamp_timezone'])

print(f"\nTimestamp range:")
print(f"Min: {df['timestamp_timezone'].min()}")
print(f"Max: {df['timestamp_timezone'].max()}")

print(f"\nTime differences between consecutive rows:")
time_diffs = df['timestamp_timezone'].diff().dropna()
print(f"Average time difference: {time_diffs.mean()}")
print(f"Min time difference: {time_diffs.min()}")
print(f"Max time difference: {time_diffs.max()}")

print(f"\nUnique machines:")
print(df['machine_number'].value_counts())
