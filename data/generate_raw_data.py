"""Synthesizes raw market feed data with intentional anomalies."""
import csv
import os
import random
import uuid
from datetime import datetime, timezone


def generate_raw_trades(
    output_path: str = os.path.join("data", "raw_trades.csv"),
    total_records: int = 1000,
) -> str:
    """Generate raw market feed containing realistic financial anomalies.

    Anomalies injected:
        - Missing/None prices
        - Null instrument names
        - Negative or zero prices / quantities
        - Duplicate trade_ids (simulating producer retries)
        - Non-standard timestamp formats

    Args:
        output_path: Filepath where the raw CSV is saved.
        total_records: Number of raw records to synthesize.

    Returns:
        str: Absolute or relative output path of generated CSV.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    instruments = ["AAPL", "GOOGL", "MSFT", "NVDA", "AMZN", "TSLA", "BTC/USD", "ETH/USD"]

    records = []
    generated_trade_ids = []

    base_time = datetime(2026, 10, 1, 9, 30, 0, tzinfo=timezone.utc)

    for i in range(total_records):
        anomaly_chance = random.random()
        trade_id = f"TRD-{uuid.uuid4().hex[:12].upper()}"

        # 4% chance: Duplicate trade ID from previously generated trades
        if anomaly_chance < 0.04 and generated_trade_ids:
            trade_id = random.choice(generated_trade_ids)
        else:
            generated_trade_ids.append(trade_id)

        # 3% chance: Missing / empty trade_id
        if 0.04 <= anomaly_chance < 0.07:
            trade_id = ""

        # 3% chance: Null or empty instrument
        if 0.07 <= anomaly_chance < 0.10:
            instrument = ""
        else:
            instrument = random.choice(instruments)

        # Base price calculation
        base_price = round(random.uniform(50.0, 3500.0), 2)

        # 4% chance: Missing price (empty)
        if 0.10 <= anomaly_chance < 0.14:
            price_str = ""
        # 3% chance: Non-positive / invalid price
        elif 0.14 <= anomaly_chance < 0.17:
            price_str = str(random.choice([-150.0, 0.0, -0.01]))
        else:
            price_str = str(base_price)

        # Base quantity
        base_qty = random.randint(1, 500)
        # 3% chance: Non-positive quantity
        if 0.17 <= anomaly_chance < 0.20:
            quantity_str = str(random.choice([0, -10, -50]))
        else:
            quantity_str = str(base_qty)

        buy_order_id = f"ORD-BUY-{uuid.uuid4().hex[:8].upper()}"
        sell_order_id = f"ORD-SELL-{uuid.uuid4().hex[:8].upper()}"

        # Timestamp generation with mixed formatting
        delta_sec = i * 0.25
        dt = datetime.fromtimestamp(base_time.timestamp() + delta_sec, tz=timezone.utc)

        if 0.20 <= anomaly_chance < 0.23:
            # Non-standard space format
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        elif 0.23 <= anomaly_chance < 0.25:
            # Epoch millisecond string
            timestamp_str = str(int(dt.timestamp() * 1000))
        else:
            # Standard ISO-8601 UTC
            timestamp_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        records.append(
            {
                "trade_id": trade_id,
                "instrument": instrument,
                "price": price_str,
                "quantity": quantity_str,
                "buy_order_id": buy_order_id,
                "sell_order_id": sell_order_id,
                "timestamp": timestamp_str,
            }
        )

    fieldnames = [
        "trade_id",
        "instrument",
        "price",
        "quantity",
        "buy_order_id",
        "sell_order_id",
        "timestamp",
    ]

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"[DATA GENERATOR] Successfully created {len(records)} raw records at {output_path}")
    return output_path


if __name__ == "__main__":
    generate_raw_trades()
