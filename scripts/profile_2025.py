import pandas as pd

FILE = "data/raw/Daily_Market_Prices_2001_2026/csv/2025.csv"

total_rows = 0
missing_cells = 0
invalid_negative = 0
invalid_price_range = 0
invalid_modal = 0

for chunk in pd.read_csv(FILE, chunksize=500_000):

    total_rows += len(chunk)

    # Missing values
    missing_cells += chunk.isna().sum().sum()

    # Negative prices
    invalid_negative += (
        (chunk["Min_Price"] < 0) |
        (chunk["Max_Price"] < 0) |
        (chunk["Modal_Price"] < 0)
    ).sum()

    # Min should not exceed Max
    invalid_price_range += (
        chunk["Min_Price"] > chunk["Max_Price"]
    ).sum()

    # Modal should normally lie between Min and Max
    invalid_modal += (
        (chunk["Modal_Price"] < chunk["Min_Price"]) |
        (chunk["Modal_Price"] > chunk["Max_Price"])
    ).sum()

print("====================================")
print("2025 DATA PROFILE")
print("====================================")
print("Total rows:", total_rows)
print("Missing cells:", missing_cells)
print("Negative-price records:", invalid_negative)
print("Min > Max records:", invalid_price_range)
print("Modal outside range:", invalid_modal)
