"""Full-Stack Mission Control HTTP & SSE Server for Hybrid Cloud Migration."""
from collections import deque
from datetime import datetime, timezone
import json
import os
import sys
import threading
import time
from typing import Any, Deque, Dict, List, Optional
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd

from data.cleanse_data import cleanse_market_data
from data.generate_raw_data import generate_raw_trades
from src.adapters.sqlite_repository import SqliteTradeRepository
from src.config.settings import get_settings
from src.domain.models import Trade
from src.use_cases.ingest_trade import IngestTradeUseCase
from src.use_cases.parity_checker import ParityCheckerUseCase


class MigrationSystemState:
    """Thread-safe state manager for hybrid cloud migration live telemetry."""

    def __init__(self) -> None:
        """Initialize repositories, use cases, and background telemetry state."""
        self.lock = threading.Lock()
        self.settings = get_settings()

        # Database paths
        self.legacy_db_path = self.settings.db.legacy_sqlite_path
        self.cloud_db_path = self.settings.db.cloud_sqlite_path

        self.legacy_repo: SqliteTradeRepository
        self.cloud_repo: SqliteTradeRepository
        self.legacy_ingest: IngestTradeUseCase
        self.cloud_ingest: IngestTradeUseCase
        self.parity_checker: ParityCheckerUseCase

        self._init_repositories()

        # Live streaming states
        self.is_streaming: bool = False
        self.is_chaos_active: bool = False
        self.is_cutover_active: bool = False
        self.target_tps: int = 20
        self.actual_tps: int = 0

        # Memory telemetry buffers
        self.trades_pool: List[Trade] = []
        self.trade_cursor: int = 0
        self.dropped_trades: List[Trade] = []
        self.recent_trades: Deque[Dict[str, Any]] = deque(maxlen=40)
        self.recent_logs: Deque[Dict[str, str]] = deque(maxlen=50)

        # Performance measurement
        self.trades_last_sec: int = 0
        self.last_tps_check: float = time.time()

        self._load_market_data_pool()
        self.log("SYSTEM", "info", "Hybrid Cloud Migration Core initialized.")

    def _init_repositories(self) -> None:
        """Initialize SQLite repositories."""
        self.legacy_repo = SqliteTradeRepository(self.legacy_db_path)
        self.cloud_repo = SqliteTradeRepository(self.cloud_db_path)
        self.legacy_ingest = IngestTradeUseCase(self.legacy_repo)
        self.cloud_ingest = IngestTradeUseCase(self.cloud_repo)
        self.parity_checker = ParityCheckerUseCase(self.legacy_repo, self.cloud_repo)

    def _load_market_data_pool(self) -> None:
        """Load or synthesize cleaned domain Trade entities."""
        clean_path = self.settings.cleaned_data_path
        raw_path = self.settings.raw_data_path

        if not os.path.exists(clean_path):
            if not os.path.exists(raw_path):
                generate_raw_trades(raw_path, total_records=1000)
            cleanse_market_data(raw_path, clean_path)

        df = pd.read_csv(clean_path)
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
            except Exception:
                continue

        self.trades_pool = trades
        self.trade_cursor = 0

    def log(self, tag: str, log_type: str, msg: str) -> None:
        """Record an audit message for the telemetry feed."""
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with self.lock:
            self.recent_logs.append({"ts": f"{tag}:{now}", "type": log_type, "msg": msg})

    def process_next_trade(self) -> Optional[Dict[str, Any]]:
        """Ingest next trade from pool into repositories with chaos handling."""
        if not self.trades_pool:
            return None

        with self.lock:
            if not self.is_streaming:
                return None

            trade = self.trades_pool[self.trade_cursor]
            self.trade_cursor = (self.trade_cursor + 1) % len(self.trades_pool)

            # Ingest to Legacy (Always recorded)
            self.legacy_ingest.execute(trade)

            # Ingest to Cloud (Shadow Mode with Chaos Hook)
            cloud_status = "STORED"
            if self.is_chaos_active:
                cloud_status = "DROPPED"
                self.dropped_trades.append(trade)
            else:
                self.cloud_ingest.execute(trade)

            trade_record = {
                "trade_id": trade.trade_id,
                "instrument": trade.instrument,
                "price": trade.price,
                "quantity": trade.quantity,
                "buy_order_id": trade.buy_order_id,
                "sell_order_id": trade.sell_order_id,
                "timestamp": trade.timestamp,
                "legacy_status": "STORED",
                "cloud_status": cloud_status,
            }
            self.recent_trades.appendleft(trade_record)

            # TPS Tracking
            self.trades_last_sec += 1
            now = time.time()
            if now - self.last_tps_check >= 1.0:
                self.actual_tps = self.trades_last_sec
                self.trades_last_sec = 0
                self.last_tps_check = now

            return trade_record

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Generate complete real-time telemetry snapshot."""
        with self.lock:
            audit = self.parity_checker.execute()
            return {
                "legacy_count": audit["legacy_count"],
                "cloud_count": audit["cloud_count"],
                "drift": audit["drift"],
                "status": audit["status"],
                "legacy_volume": audit["legacy_volume"],
                "cloud_volume": audit["cloud_volume"],
                "volume_difference": audit["volume_difference"],
                "is_streaming": self.is_streaming,
                "is_chaos_active": self.is_chaos_active,
                "is_cutover_active": self.is_cutover_active,
                "tps": self.actual_tps or (self.target_tps if self.is_streaming else 0),
                "latest_trades": list(self.recent_trades)[:15],
                "recent_logs": list(self.recent_logs)[-8:],
            }

    def reconcile_drift(self) -> Dict[str, Any]:
        """Perform out-of-band reconciliation replay for missing trade IDs."""
        with self.lock:
            missing_ids = self.parity_checker.get_missing_cloud_ids()
            replayed = 0
            for trade in list(self.dropped_trades):
                if trade.trade_id in missing_ids:
                    inserted = self.cloud_ingest.execute(trade)
                    if inserted:
                        replayed += 1
            self.dropped_trades.clear()
            audit = self.parity_checker.execute()

        self.log(
            "RECON",
            "success",
            f"Idempotent replay restored {replayed} missing trades. Parity: {audit['status']}.",
        )
        return {"replayed": replayed, "status": audit["status"]}

    def reset_databases(self) -> None:
        """Reset databases and restart ingestion from beginning."""
        with self.lock:
            self.is_streaming = False
            self.is_chaos_active = False
            self.is_cutover_active = False
            self.legacy_repo.close()
            self.cloud_repo.close()

            for db_path in [self.legacy_db_path, self.cloud_db_path]:
                if os.path.exists(db_path):
                    try:
                        os.remove(db_path)
                    except OSError:
                        pass

            self._init_repositories()
            self.dropped_trades.clear()
            self.recent_trades.clear()
            self.trade_cursor = 0
            self.actual_tps = 0

        self.log("SYSTEM", "info", "Databases reset to initial state.")


# Global system state instance
SYSTEM_STATE = MigrationSystemState()


def background_stream_worker() -> None:
    """Continuous background worker pushing trades at designated target TPS."""
    while True:
        if SYSTEM_STATE.is_streaming:
            SYSTEM_STATE.process_next_trade()
            delay = 1.0 / max(1, SYSTEM_STATE.target_tps)
            time.sleep(delay)
        else:
            time.sleep(0.1)


class MissionControlHandler(SimpleHTTPRequestHandler):
    """HTTP Request handler serving UI assets and JSON / SSE endpoints."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize handler serving web directory."""
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests for static assets and SSE streams."""
        if self.path == "/api/status":
            self._send_json(SYSTEM_STATE.get_telemetry_snapshot())
            return

        if self.path == "/api/events":
            self._handle_sse_stream()
            return

        if self.path == "/openapi.json":
            spec_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "docs", "openapi.json"
            )
            if os.path.exists(spec_file):
                with open(spec_file, "r", encoding="utf-8") as f:
                    self._send_json(json.load(f))
                return

        if self.path == "/docs":
            self.path = "/docs.html"

        # Serve static web files
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        """Handle REST control actions."""
        if self.path == "/api/stream/toggle":
            with SYSTEM_STATE.lock:
                SYSTEM_STATE.is_streaming = not SYSTEM_STATE.is_streaming
                state = SYSTEM_STATE.is_streaming
            SYSTEM_STATE.log(
                "STREAM",
                "info",
                f"Market stream {'RESUMED' if state else 'PAUSED'}.",
            )
            self._send_json({"is_streaming": state})
            return

        if self.path == "/api/chaos/toggle":
            with SYSTEM_STATE.lock:
                SYSTEM_STATE.is_chaos_active = not SYSTEM_STATE.is_chaos_active
                chaos = SYSTEM_STATE.is_chaos_active
            action = "INJECTED: Cloud worker dropping trades!" if chaos else "HEALED."
            SYSTEM_STATE.log("CHAOS", "alert" if chaos else "success", f"Outage {action}")
            self._send_json({"is_chaos_active": chaos})
            return

        if self.path == "/api/stream/speed":
            body = self._read_json_body()
            tps = int(body.get("tps", 20))
            with SYSTEM_STATE.lock:
                SYSTEM_STATE.target_tps = max(1, min(100, tps))
            self._send_json({"target_tps": SYSTEM_STATE.target_tps})
            return

        if self.path == "/api/reconcile":
            result = SYSTEM_STATE.reconcile_drift()
            self._send_json(result)
            return

        if self.path == "/api/cutover":
            with SYSTEM_STATE.lock:
                SYSTEM_STATE.is_cutover_active = True
            SYSTEM_STATE.log("CUTOVER", "success", "Cloud Aurora promoted to Primary Master.")
            self._send_json({"is_cutover_active": True})
            return

        if self.path == "/api/reset":
            SYSTEM_STATE.reset_databases()
            self._send_json({"status": "RESET_COMPLETE"})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _handle_sse_stream(self) -> None:
        """Establish persistent Server-Sent Events stream."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            while True:
                snapshot = SYSTEM_STATE.get_telemetry_snapshot()
                payload = f"data: {json.dumps(snapshot)}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.2)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json_body(self) -> Dict[str, Any]:
        """Read and parse incoming JSON payload."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            data = self.rfile.read(content_length).decode("utf-8")
            return json.loads(data)
        return {}

    def _send_json(self, data: Dict[str, Any]) -> None:
        """Serialize and transmit JSON response."""
        payload = json.dumps(data).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard HTTP request console logging for clean terminal."""
        pass


def run_server(port: int = 8080) -> None:
    """Launch multi-threaded server and background streaming worker."""
    # Spawn background streaming worker
    worker_thread = threading.Thread(
        target=background_stream_worker, name="StreamWorker", daemon=True
    )
    worker_thread.start()

    # Bind HTTP Server
    server_address = ("127.0.0.1", port)
    try:
        httpd = ThreadingHTTPServer(server_address, MissionControlHandler)
    except OSError:
        # Fallback to alternate port
        port = 8000
        server_address = ("127.0.0.1", port)
        httpd = ThreadingHTTPServer(server_address, MissionControlHandler)

    print("=" * 80)
    print(" [LAUNCH] NEXUS EXCHANGE // HYBRID CLOUD MIGRATION MISSION CONTROL")
    print(f" Live Web Interface: http://localhost:{port}/")
    print("=" * 80)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port=port_arg)
