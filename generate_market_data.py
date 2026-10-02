import pandas as pd
import numpy as np
from datetime import datetime, timedelta

NUM_TRADES = 25000
instruments = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
base_prices = {"AAPL": 180.0, "MSFT": 420.0, "GOOGL": 175.0, "AMZN": 185.0, "NVDA": 120.0, "TSLA": 250.0}

print(f"Generating {NUM_TRADES} realistic securities trades matching competition schema...")

start_time = datetime(2026, 9, 22, 9, 30, 0)
timestamps = [start_time + timedelta(milliseconds=i * 25) for i in range(NUM_TRADES)]
selected_inst = np.random.choice(instruments, NUM_TRADES)

prices = [
    round(base_prices[sym] + np.random.normal(0, 0.5), 2)
    for sym in selected_inst
]
quantities = np.random.choice([10, 50, 100, 200, 500, 1000], NUM_TRADES)

df = pd.DataFrame({
    "trade_id": [f"TRD_{100000 + i}" for i in range(NUM_TRADES)],
    "buy_order_id": [f"ORD_B_{200000 + i}" for i in range(NUM_TRADES)],
    "sell_order_id": [f"ORD_S_{300000 + i}" for i in range(NUM_TRADES)],
    "instrument": selected_inst,
    "price": prices,
    "quantity": quantities,
    "timestamp": [ts.isoformat() for ts in timestamps]
})

df.to_csv("market_trades.csv", index=False)
print("Saved market_trades.csv successfully!")
print(df.head(5))