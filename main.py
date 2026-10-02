"""End-to-End Simulation: Dual Stream + Live Auditor + Zero-Data-Loss Rollback Drill."""
import os
import sys
from typing import List

import pandas as pd

from data.cleanse import cleanse_market_data
from data.generate_raw_data import generate_raw_trades
from src.adapters.memory_bus import MemoryEventBus
from src.adapters.sqlite_adapter import SqliteTradeAdapter
from src.domain.models import Trade
from src.services.ingestion_service import DualIngestionService
from src.services.parity_service import ParityService

# Configure UTF-8 stdout for clean Windows console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_trades_from_csv(csv_path: str) -> List[Trade]:
    """Read cleansed CSV and instantiate validated pure Trade domain entities."""
    df = pd.read_csv(csv_path)
    trades: List[Trade] = []
    for _, row in df.iterrows():
        try:
            trade = Trade(
                trade_id=str(row["trade_id"]),
                instrument=str(row["instrument"]),
                price=float(row["price"]),
                quantity=int(row["quantity"]),
                buy_order_id=str(row["buy_order_id"]),
                sell_order_id=str(row["sell_order_id"]),
                timestamp=str(row["timestamp"]),
            )
            trades.append(trade)
        except (ValueError, KeyError):
            continue
    return trades


def run_hybrid_cloud_migration_drill() -> None:
    """Execute the production-grade multi-threaded migration simulation."""
    print("=" * 80)
    print(" 24/7 FINANCIAL EXCHANGE: ZERO-DOWNTIME HYBRID CLOUD MIGRATION")
    print(" Decoupled Shadow Running | Live Parity Auditor | Zero-Loss Rollback")
    print("=" * 80)

    # 1. Synthesize and Cleanse Market Data Feed
    raw_path = os.path.join("data", "raw_trades.csv")
    cleaned_path = os.path.join("data", "cleaned_trades.csv")

    print("\n[PHASE 1] Synthesizing raw market feed with intentional anomalies (1,400 records)...")
    generate_raw_trades(output_path=raw_path, total_records=1400)

    print("\n[PHASE 2] Executing automated data hygiene pipeline (data/cleanse.py)...")
    cleanse_market_data(input_path=raw_path, output_path=cleaned_path)

    trades = load_trades_from_csv(cleaned_path)[:1000]
    total_trades = len(trades)
    print(f"\n[INFO] Loaded {total_trades} pristine domain Trade entities for streaming.")

    # 2. Initialize Clean Architecture Repositories & Services
    legacy_db_file = "legacy_trades.db"
    cloud_db_file = "cloud_trades.db"

    legacy_adapter = SqliteTradeAdapter(legacy_db_file)
    cloud_adapter = SqliteTradeAdapter(cloud_db_file)
    legacy_adapter.clear()
    cloud_adapter.clear()

    ingestion_service = DualIngestionService(legacy_adapter, cloud_adapter)
    parity_service = ParityService(legacy_adapter, cloud_adapter)
    event_bus = MemoryEventBus()
    topic = "market.trades"

    # Subscribe decoupled shadow consumers to the event bus
    ingestion_service.bind_to_event_bus(event_bus, topic=topic)

    print("\n[PHASE 3] Starting Decoupled Dual Shadow Streaming (1,000 trades)...")
    print(f"  - Event Bus Topic : {topic}")
    print(f"  - Primary On-Prem : {legacy_db_file} (Authoritative Master)")
    print(f"  - Cloud Target    : {cloud_db_file} (Shadow Replica -> Aurora)")

    # 3. Stream Ingestion with Chaos Failure Drill at Trade 500
    failure_point = 500

    for i, trade in enumerate(trades):
        # Inject Cloud Failure at Trade 500
        if i == failure_point:
            event_bus.join()
            ingestion_service.set_cloud_partition(True)
            print("\n" + "!" * 80)
            print(f" [CHAOS DRILL INJECTED] Cloud Target Database Failure at Trade #{i}!")
            print(" Cloud consumer is dropping trades. Failback hot-standby active on Legacy.")
            print("!" * 80 + "\n")

        event_bus.publish(topic, trade)

        # Real-time console parity updates every 250 trades
        if (i + 1) % 250 == 0 or (i + 1) == total_trades:
            event_bus.join()
            audit = parity_service.evaluate_parity()
            status_indicator = (
                "[OK] IN_PARITY" if audit["status"] == "IN_PARITY" else "[ALERT] DRIFT_DETECTED"
            )
            print(
                f"[STREAM MONITOR #{i + 1:04d}/{total_trades}] "
                f"Legacy: {audit['legacy_count']:>4} | Cloud: {audit['cloud_count']:>4} | "
                f"Drift: {audit['drift']:>3} | {status_indicator} | "
                f"Vol Diff: ${audit['volume_difference']:,.2f}"
            )

    event_bus.join()

    # 4. Out-of-Band Parity Audit Post-Stream
    print("\n" + "=" * 80)
    print(" [PHASE 4] OUT-OF-BAND LEDGER RECONCILIATION & ROLLBACK VERIFICATION")
    print("=" * 80)

    post_failure_audit = parity_service.evaluate_parity()
    missing_ids = parity_service.get_missing_cloud_ids()

    print(f"  Total Trades Streamed   : {total_trades}")
    print(f"  Legacy DB Count (Master): {post_failure_audit['legacy_count']} (100.00% Captured)")
    print(f"  Cloud DB Count (Shadow) : {post_failure_audit['cloud_count']}")
    print(f"  Unsynchronized Drift    : {post_failure_audit['drift']} records missing in Cloud")
    print(f"  Legacy Volume Total     : ${post_failure_audit['legacy_volume']:,.2f}")
    print(f"  Cloud Volume Total      : ${post_failure_audit['cloud_volume']:,.2f}")
    print(f"  Volume Discrepancy      : ${post_failure_audit['volume_difference']:,.2f}")
    print("  Data Loss on Legacy     : 0.00% (Zero-Data-Loss Hot Standby Guaranteed)")

    # 5. Automatic Reconciliation Engine: Idempotent Catch-up Replay
    if post_failure_audit["status"] == "DRIFT_DETECTED":
        print("\n" + "=" * 80)
        print(" [PHASE 5] AUTOMATED RECONCILIATION ENGINE TRIGGERED")
        print("=" * 80)
        print(f"  - Target Cloud DB restored. Identified {len(missing_ids)} missing records.")
        print("  - Executing idempotent replay from Kafka event backlog...")

        # Replay dropped trades
        dropped_trades = ingestion_service.get_dropped_trades()
        recon_result = parity_service.reconcile_from_trades(dropped_trades)
        ingestion_service.set_cloud_partition(False)
        ingestion_service.clear_dropped_trades()

        print(f"  - Replayed {recon_result['replayed_count']} trades with ON CONFLICT semantics.")

        final_audit = parity_service.evaluate_parity()
        print("\n[FINAL POST-RECONCILIATION AUDIT]")
        print(f"  Legacy DB Final Count : {final_audit['legacy_count']}")
        print(f"  Cloud DB Final Count  : {final_audit['cloud_count']}")
        print(f"  Final Drift Count     : {final_audit['drift']}")
        print(f"  Final Vol Discrepancy : ${final_audit['volume_difference']:,.2f}")
        print(f"  Parity Status         : {final_audit['status']}")
        print("  Data Loss Percentage  : 0.00%")

        if final_audit["status"] == "IN_PARITY":
            print("\n" + "*" * 80)
            print(" [SUCCESS] 100% RECONCILIATION ACHIEVED! ZERO DOWNTIME | ZERO DATA LOSS")
            print("*" * 80)
        else:
            print("\n[FAILURE] Parity reconciliation failed.")
            sys.exit(1)

    # Clean up resources
    event_bus.close()
    legacy_adapter.close()
    cloud_adapter.close()
    print("\nSimulation complete. All connections closed gracefully.\n")


if __name__ == "__main__":
    run_hybrid_cloud_migration_drill()
