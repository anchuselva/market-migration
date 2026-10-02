import pandas as pd

# Load the file
df = pd.read_csv("trades.csv")

print("--- DATA SUMMARY ---")
print(f"Total Rows: {len(df)}")
print("\nColumns:")
print(list(df.columns))

print("\nFirst 3 rows:")
print(df.head(3))