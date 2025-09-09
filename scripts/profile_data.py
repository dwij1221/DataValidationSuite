import pandas as pd
import os

# locate latest file in data/raw
raw_dir = "../data/raw"
files = sorted(os.listdir(raw_dir))
latest_file = [f for f in files if f.endswith(".csv")][-1]
path = os.path.join(raw_dir, latest_file)

print("📂 Profiling file:", path)

df = pd.read_csv(path, parse_dates=["date"])

# Basic info
print("\n--- Dataset Shape ---")
print(df.shape)

print("\n--- Columns & Types ---")
print(df.dtypes)

print("\n--- Missing Values ---")
print(df.isna().sum())

print("\n--- Sample Rows ---")
print(df.head(5))

print("\n--- Descriptive Stats ---")
print(df.describe())

# Quick checks
print("\n--- Negative revenues ---")
print(df[df["revenue"] < 0].head())

print("\n--- Duplicates ---")
print(df.duplicated().sum())
