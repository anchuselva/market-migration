"""Entry point and live simulation for Hybrid Cloud Migration system."""
import os
import sys
from typing import List

import pandas as pd

from data.cleanse_data import cleanse_market_data
from data.generate_raw_data import generate_raw_trades
from src.adapters.queue_stream import QueueEventStream
from src.adapters.sqlite_repository import SqliteTradeRepository
from src.config.settings import get_settings
from src.domain.models import Trade
from src.use_cases.ingest_trade import IngestTradeUseCase
from src.use_cases.parity_checker import ParityCheckerUseCase


def load_cleaned_trades(csv_path: str) -> List[Trade]:
    """Read cleaned CSV and construct pure domain Trade entities.

    Args:
        csv_path: Path to cleaned trades CSV.

    Returns:
        List[Trade]: Validated domain models.
    """
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
        except (ValueError, KeyError) as err:
            print(f"[LOAD WARNING] Skipping invalid row: {err}")
    return trades


def run_hybrid_cloud_migration_simulation() -> None:
    """Execute the end-to-end decoupled shadow running simulation."""
    settings = get_settings()

    print("=" * 80)
    print(" 24/7 FINANCIAL EXCHANGE: HYBRID CLOUD MIGRATION SYSTEM")
    print(" Decoupled Shadow Running Pattern & Out-of-Band Parity Auditor")
    print("=" * 80)

    # 1. Prepare Data Pipeline
    raw_path = settings.raw_data_path
    clean_path = settings.cleaned_data_path

    print("\n[PHASE 1] Synthesizing fresh raw market feed with intentional anomalies...")
    generate_raw_trades(output_path=raw_path, total_records=1000)

    print("\n[PHASE 2] Executing automated data cleansing pipeline...")
    cleanse_market_data(input_path=raw_path, output_path=clean_path)

    trades = load_cleaned_trades(clean_path)
    total_trades = len(trades)
    print(f"\n[INFO] Loaded {total_trades} pristine domain Trade entities for streaming.")

    # 2. Reset / Initialize Repositories
    legacy_db = settings.db.legacy_sqlite_path
    cloud_db = settings.db.cloud_sqlite_path

    for db_file in [legacy_db, cloud_db]:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass

    legacy_repo = SqliteTradeRepository(legacy_db)
    cloud_repo = SqliteTradeRepository(cloud_db)

    legacy_ingest = IngestTradeUseCase(legacy_repo)
    cloud_ingest = IngestTradeUseCase(cloud_repo)
    parity_checker = ParityCheckerUseCase(legacy_repo, cloud_repo)

    # 3. Setup Decoupled Event Stream
    stream = QueueEventStream()
    topic = settings.stream.trade_topic

    # State for chaos injection hook
    chaos_state = {
        "partition_active": False,
        "dropped_by_chaos": []
    }

    # Legacy Consumer (Always processes and writes)
    def legacy_consumer(trade: Trade) -> None:
        legacy_ingest.execute(trade)

    # Cloud Consumer (Shadow runner with simulated chaos hook)
    def cloud_consumer(trade: Trade) -> None:
        if chaos_state["partition_active"]:
            # Simulate temporary network drop / transient cloud service degradation
            chaos_state["dropped_by_chaos"].append(trade)
            return
        cloud_ingest.execute(trade)

    stream.subscribe(topic, legacy_consumer)
    stream.subscribe(topic, cloud_consumer)

    print("\n[PHASE 3] Starting Decoupled Dual Shadow Streaming via Event Stream...")
    print(f"  - Topic: {topic}")
    print(f"  - Legacy Store: {legacy_db}")
    print(f"  - Cloud Shadow Store: {cloud_db}")

    # 4. Stream Ingestion with Chaos Hook
    # Inject chaos between trades 300 and 380 to simulate a transient network hiccup
    chaos_start = 300
    chaos_end = 380

    for i, trade in enumerate(trades):
        if i == chaos_start:
            stream.join()
            chaos_state["partition_active"] = True
            print(
                f"\n[CHAOS HOOK INJECTED] "
                f"Simulated transient network outage to Cloud AZ at trade #{i}!"
            )

        if i == chaos_end:
            stream.join()
            chaos_state["partition_active"] = False
            print(f"[CHAOS HOOK CLEARED] Cloud connection restored at trade #{i}!\n")

        stream.publish(topic, trade)

        # Periodic audit log during streaming
        if (i + 1) % 200 == 0 or (i + 1) == total_trades:
            stream.join()
            audit = parity_checker.execute()
            status_indicator = (
                "[OK] IN_PARITY" if audit["status"] == "IN_PARITY" else "[ALERT] DRIFT_DETECTED"
            )
            vol_diff_fmt = f"${audit['volume_difference']:,.2f}"
            print(
                f"[STREAM AUDIT #{i + 1:04d}/{total_trades}] "
                f"Legacy: {audit['legacy_count']} | Cloud: {audit['cloud_count']} | "
                f"Drift: {audit['drift']} | {status_indicator} | Vol Diff: {vol_diff_fmt}"
            )

    stream.join()

    # 5. Out-of-Band Parity Audit Post-Run
    print("\n" + "=" * 80)
    print(" [PHASE 4] OUT-OF-BAND CONTINUOUS PARITY AUDITOR EVALUATION")
    print("=" * 80)

    audit_result = parity_checker.execute()
    print(f"  Legacy DB Count:     {audit_result['legacy_count']}")
    print(f"  Cloud DB Count:      {audit_result['cloud_count']}")
    print(f"  Trade Drift Count:   {audit_result['drift']}")
    print(f"  Legacy Total Volume: ${audit_result['legacy_volume']:,.2f}")
    print(f"  Cloud Total Volume:  ${audit_result['cloud_volume']:,.2f}")
    print(f"  Volume Discrepancy:  ${audit_result['volume_difference']:,.2f}")
    print(f"  Parity Status:       {audit_result['status']}")

    # 6. Automatic Failback / Reconciliation Replay
    if audit_result["status"] == "DRIFT_DETECTED":
        missing_ids = parity_checker.get_missing_cloud_ids()
        print("\n[PHASE 5] AUTOMATIC RECONCILIATION ENGINE TRIGGERED:")
        print(f"  - Detected {len(missing_ids)} missing trade IDs in Cloud Shadow DB.")
        print("  - Executing idempotent replay from Kafka event backlog / store...")

        # Replay the dropped trades
        dropped_trades: List[Trade] = chaos_state["dropped_by_chaos"]
        replayed_count = 0
        for trade in dropped_trades:
            if trade.trade_id in missing_ids:
                inserted = cloud_ingest.execute(trade)
                if inserted:
                    replayed_count += 1

        print(
            f"  - Successfully replayed {replayed_count} trades with "
            f"idempotent ON CONFLICT semantics."
        )

        # Re-run parity audit
        reconciled_audit = parity_checker.execute()
        print("\n[FINAL POST-RECONCILIATION AUDIT]")
        print(f"  Legacy DB Count:     {reconciled_audit['legacy_count']}")
        print(f"  Cloud DB Count:      {reconciled_audit['cloud_count']}")
        print(f"  Trade Drift Count:   {reconciled_audit['drift']}")
        print(f"  Legacy Volume:       ${reconciled_audit['legacy_volume']:,.2f}")
        print(f"  Cloud Volume:        ${reconciled_audit['cloud_volume']:,.2f}")
        print(f"  Volume Discrepancy:  ${reconciled_audit['volume_difference']:,.2f}")
        print(f"  Parity Status:       {reconciled_audit['status']}")

        if reconciled_audit["status"] == "IN_PARITY":
            print("\n[SUCCESS] 100% RECONCILIATION ACHIEVED! ZERO DATA LOSS. ZERO DOWNTIME.")
        else:
            print("\n[FAILURE] System failed to achieve parity.")
            sys.exit(1)

    # Cleanup resources
    stream.close()
    legacy_repo.close()
    cloud_repo.close()
    print("=" * 80)


if __name__ == "__main__":
    run_hybrid_cloud_migration_simulation()
