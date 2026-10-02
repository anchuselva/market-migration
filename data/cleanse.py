"""Data hygiene script for financial market trade feeds using pandas.

Cleanses synthetic dirty raw market data:
- Drops records with null or blank trade_id, instrument, or price
- Removes records with negative or zero price and quantity
- Eliminates duplicate trade IDs
- Normalizes all timestamp formats to standard ISO 8601 UTC ('YYYY-MM-DDTHH:MM:SSZ')
- Outputs cleaned, validated dataset to data/cleaned_trades.csv
"""
import os
import sys
from typing import Optional
import pandas as pd


def normalize_iso8601(timestamp_val: object) -> Optional[str]:
    """Parse and convert various raw timestamp representations to ISO-8601 UTC.

    Supports epoch milliseconds, seconds, and standard date strings.

    Args:
        timestamp_val: Raw timestamp input.

    Returns:
        Optional[str]: Standardized ISO-8601 UTC string or None if invalid.
    """
    if pd.isna(timestamp_val):
        return None

    raw_str = str(timestamp_val).strip()
    if not raw_str or raw_str.lower() in {"nan", "none", "null"}:
        return None

    # Handle numeric epoch timestamp (ms or s)
    if raw_str.isdigit():
        val = int(raw_str)
        unit = "ms" if val > 10**11 else "s"
        try:
            dt = pd.to_datetime(val, unit=unit, utc=True)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None

    try:
        dt = pd.to_datetime(raw_str, utc=True)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def cleanse_market_data(
    input_path: str = os.path.join("data", "raw_trades.csv"),
    output_path: str = os.path.join("data", "cleaned_trades.csv"),
) -> pd.DataFrame:
    """Sanitize raw trade feed according to strict financial compliance rules.

    Args:
        input_path: Path to raw dirty CSV file.
        output_path: Destination path for cleaned output CSV.

    Returns:
        pd.DataFrame: Cleaned and validated trade records DataFrame.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Source raw data file not found at: {input_path}")

    print(f"[CLEANSE] Loading raw market feed from: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    initial_records = len(df)

    # 1. Strip string identifiers and drop rows with missing IDs
    for col in ["trade_id", "instrument", "buy_order_id", "sell_order_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df = df[df[col].notna() & (df[col] != "") & (df[col].str.lower() != "nan")]

    # 2. Coerce price and quantity to numeric
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    # Drop nulls, negative values, and zeros for price and quantity
    df = df.dropna(subset=["price", "quantity"])
    df = df[(df["price"] > 0.0) & (df["quantity"] > 0)]
    df["quantity"] = df["quantity"].astype(int)

    # 3. Deduplicate trade_id (keep first occurrence)
    df = df.drop_duplicates(subset=["trade_id"], keep="first")

    # 4. Standardize timestamps to ISO 8601 UTC
    df["timestamp"] = df["timestamp"].apply(normalize_iso8601)
    df = df.dropna(subset=["timestamp"])

    # 5. Persist to output CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    retained_records = len(df)
    dropped_records = initial_records - retained_records
    drop_pct = (dropped_records / initial_records) * 100
    print("[CLEANSE COMPLETE]")
    print(f"  - Initial dirty records : {initial_records}")
    print(f"  - Cleaned valid records : {retained_records}")
    print(f"  - Dropped invalid rows  : {dropped_records} ({drop_pct:.2f}%)")
    print(f"  - Cleaned dataset saved : {output_path}")

    return df


if __name__ == "__main__":
    src_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "raw_trades.csv")
    dest_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join("data", "cleaned_trades.csv")
    cleanse_market_data(src_file, dest_file)
