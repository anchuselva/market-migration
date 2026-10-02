import sqlite3
import pandas as pd
import time
import queue
import threading

# 1. Initialize DBs
def init_databases():
    schema = """
    CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY,
        buy_order_id TEXT NOT NULL,
        sell_order_id TEXT NOT NULL,
        instrument TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    for db_file in ["legacy_trades.db", "cloud_trades.db"]:
        conn = sqlite3.connect(db_file)
        conn.execute(schema)
        conn.commit()
        conn.close()

init_databases()

# Dedicated stream queues for true parallel dual-consumption
legacy_queue = queue.Queue()
cloud_queue = queue.Queue()
stream_running = True

def legacy_worker():
    conn = sqlite3.connect("legacy_trades.db")
    cur = conn.cursor()
    while stream_running or not legacy_queue.empty():
        try:
            trade = legacy_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO trades (trade_id, buy_order_id, sell_order_id, instrument, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade["trade_id"], trade["buy_order_id"], trade["sell_order_id"],
              trade["instrument"], trade["price"], trade["quantity"], trade["timestamp"]))
        conn.commit()
        legacy_queue.task_done()
    conn.close()

def cloud_worker():
    conn = sqlite3.connect("cloud_trades.db")
    cur = conn.cursor()
    while stream_running or not cloud_queue.empty():
        try:
            trade = cloud_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO trades (trade_id, buy_order_id, sell_order_id, instrument, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade["trade_id"], trade["buy_order_id"], trade["sell_order_id"],
              trade["instrument"], trade["price"], trade["quantity"], trade["timestamp"]))
        conn.commit()
        cloud_queue.task_done()
    conn.close()

threading.Thread(target=legacy_worker, daemon=True).start()
threading.Thread(target=cloud_worker, daemon=True).start()

df = pd.read_csv("market_trades.csv")
print(f"[STREAM] Dispatching {len(df)} trades concurrently...")

try:
    for idx, row in df.iterrows():
        trade_data = row.to_dict()
        legacy_queue.put(trade_data)
        cloud_queue.put(trade_data)
        time.sleep(0.003)
except KeyboardInterrupt:
    pass

stream_running = False
print("[STREAM] Stream finished.")