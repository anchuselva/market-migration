"""Data cleansing pipeline sanitizing raw market feeds using pandas."""
import os
from typing import Optional
import pandas as pd


def parse_and_standardize_timestamp(ts: object) -> Optional[str]:
    """Parse various timestamp representations into standardized ISO-8601 UTC string.

    Args:
        ts: Raw timestamp string or numeric value.

    Returns:
        Optional[str]: Standardized 'YYYY-MM-DDTHH:MM:SSZ' format or None if unparseable.
    """
    if pd.isna(ts):
        return None

    ts_str = str(ts).strip()
    if not ts_str:
        return None

    # Handle numeric epoch timestamp (ms or s)
    if ts_str.isdigit():
        val = int(ts_str)
        # If timestamp is > 10^11 it's in milliseconds
        unit = "ms" if val > 10**11 else "s"
        try:
            dt = pd.to_datetime(val, unit=unit, utc=True)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None

    # Handle standard datetime strings
    try:
        dt = pd.to_datetime(ts_str, utc=True)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def cleanse_market_data(
    input_path: str = os.path.join("data", "raw_trades.csv"),
    output_path: str = os.path.join("data", "cleaned_trades.csv"),
) -> pd.DataFrame:
    """Sanitize raw trade feed using pandas according to strict financial compliance rules.

    Sanitization rules:
        1. Drops records with missing trade_id, instrument, or price.
        2. Drops duplicate trade_ids (keeping first occurrence).
        3. Enforces strictly positive prices (price > 0).
        4. Enforces strictly positive quantities (quantity > 0).
        5. Standardizes all timestamps to ISO-8601 UTC.
        6. Persists output to cleaned CSV.

    Args:
        input_path: Path to raw CSV file.
        output_path: Destination path for cleaned CSV.

    Returns:
        pd.DataFrame: Cleaned and validated DataFrame.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, dtype=str)
    initial_count = len(df)

    # 1. Clean strings and drop rows missing essential identifiers
    df["trade_id"] = df["trade_id"].astype(str).str.strip()
    df["instrument"] = df["instrument"].astype(str).str.strip()

    df = df[df["trade_id"].notna() & (df["trade_id"] != "") & (df["trade_id"] != "nan")]
    df = df[df["instrument"].notna() & (df["instrument"] != "") & (df["instrument"] != "nan")]

    # 2. Coerce price and quantity to numeric, dropping NaNs and non-positive numbers
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    df = df.dropna(subset=["price", "quantity"])
    df = df[(df["price"] > 0) & (df["quantity"] > 0)]
    df["quantity"] = df["quantity"].astype(int)

    # 3. Drop duplicate trade_ids
    df = df.drop_duplicates(subset=["trade_id"], keep="first")

    # 4. Standardize timestamps to ISO-8601 UTC
    df["timestamp"] = df["timestamp"].apply(parse_and_standardize_timestamp)
    df = df.dropna(subset=["timestamp"])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Persist cleaned dataset
    df.to_csv(output_path, index=False)

    print(
        f"[DATA CLEANSER] Cleansing complete:\n"
        f"  - Initial raw records: {initial_count}\n"
        f"  - Cleaned valid records: {len(df)}\n"
        f"  - Dropped invalid/duplicate: {initial_count - len(df)}\n"
        f"  - Output saved to: {output_path}"
    )

    return df


if __name__ == "__main__":
    cleanse_market_data()
