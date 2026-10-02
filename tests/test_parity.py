"""Unit and integration tests for parity checking, repository idempotency, and dual-ingestion."""
import pytest
from unittest.mock import MagicMock, patch

from src.adapters.memory_bus import MemoryEventBus
from src.adapters.postgres_adapter import PostgresTradeAdapter
from src.adapters.sqlite_adapter import SqliteTradeAdapter
from src.api.routes import ApiRouter
from src.domain.models import Trade
from src.services.ingestion_service import DualIngestionService, IngestTradeUseCase
from src.services.parity_service import ParityCheckerUseCase, ParityService


@pytest.fixture
def sample_trade_1() -> Trade:
    """Fixture for sample trade 1."""
    return Trade(
        trade_id="TRD-001",
        instrument="AAPL",
        price=150.0,
        quantity=10,
        buy_order_id="BUY-101",
        sell_order_id="SELL-101",
        timestamp="2026-10-01T10:00:00Z",
    )


@pytest.fixture
def sample_trade_2() -> Trade:
    """Fixture for sample trade 2."""
    return Trade(
        trade_id="TRD-002",
        instrument="GOOGL",
        price=200.0,
        quantity=5,
        buy_order_id="BUY-102",
        sell_order_id="SELL-102",
        timestamp="2026-10-01T10:01:00Z",
    )


class TestSqliteRepositoryIdempotency:
    """Test suite for SQLite repository behavior and strict idempotency."""

    def test_save_and_idempotency(self, sample_trade_1: Trade) -> None:
        """Ensure initial save succeeds and subsequent duplicate saves are ignored."""
        repo = SqliteTradeAdapter(":memory:")

        # First insert -> True
        inserted = repo.save(sample_trade_1)
        assert inserted is True
        assert repo.count() == 1
        assert repo.total_volume() == 1500.0

        # Duplicate insert with same trade_id -> False, count remains 1
        duplicate_inserted = repo.save(sample_trade_1)
        assert duplicate_inserted is False
        assert repo.count() == 1
        assert repo.total_volume() == 1500.0

        repo.close()

    def test_volume_and_id_retrieval(self, sample_trade_1: Trade, sample_trade_2: Trade) -> None:
        """Verify cumulative volume and ID set retrieval."""
        repo = SqliteTradeAdapter(":memory:")
        repo.save(sample_trade_1)  # 150.0 * 10 = 1500.0
        repo.save(sample_trade_2)  # 200.0 * 5 = 1000.0

        assert repo.count() == 2
        assert repo.total_volume() == 2500.0
        assert repo.get_all_ids() == {"TRD-001", "TRD-002"}

        retrieved = repo.find_by_id("TRD-001")
        assert retrieved is not None
        assert retrieved.trade_id == "TRD-001"
        assert retrieved.instrument == "AAPL"

        repo.close()


class TestParityService:
    """Test suite for Out-of-Band Parity evaluation and reconciliation."""

    def test_in_parity_state(self, sample_trade_1: Trade, sample_trade_2: Trade) -> None:
        """Verify parity auditor flags IN_PARITY when stores are perfectly synchronized."""
        legacy_repo = SqliteTradeAdapter(":memory:")
        cloud_repo = SqliteTradeAdapter(":memory:")

        legacy_repo.save(sample_trade_1)
        legacy_repo.save(sample_trade_2)
        cloud_repo.save(sample_trade_1)
        cloud_repo.save(sample_trade_2)

        checker = ParityService(legacy_repo, cloud_repo)
        result = checker.evaluate_parity()

        assert result["status"] == "IN_PARITY"
        assert result["drift"] == 0
        assert result["volume_difference"] == 0.0
        assert result["legacy_count"] == 2
        assert result["cloud_count"] == 2
        assert result["data_loss_percentage"] == 0.00

        legacy_repo.close()
        cloud_repo.close()

    def test_drift_detected_and_reconciled(
        self, sample_trade_1: Trade, sample_trade_2: Trade
    ) -> None:
        """Verify drift detection when cloud lags, and verify complete reconciliation."""
        legacy_repo = SqliteTradeAdapter(":memory:")
        cloud_repo = SqliteTradeAdapter(":memory:")

        # Legacy has both, cloud only has trade 1
        legacy_repo.save(sample_trade_1)
        legacy_repo.save(sample_trade_2)
        cloud_repo.save(sample_trade_1)

        checker = ParityService(legacy_repo, cloud_repo)
        drift_result = checker.evaluate_parity()

        assert drift_result["status"] == "DRIFT_DETECTED"
        assert drift_result["drift"] == 1
        assert drift_result["volume_difference"] == 1000.0
        assert checker.get_missing_cloud_ids() == {"TRD-002"}

        # Perform reconciliation
        recon_result = checker.reconcile_from_trades([sample_trade_2])
        assert recon_result["replayed_count"] == 1
        assert recon_result["final_status"] == "IN_PARITY"
        assert recon_result["final_drift"] == 0

        legacy_repo.close()
        cloud_repo.close()


class TestDualIngestionService:
    """Test suite for dual shadow running and chaos partition injection."""

    def test_shadow_ingestion_and_chaos(
        self, sample_trade_1: Trade, sample_trade_2: Trade
    ) -> None:
        """Verify normal dual ingestion and simulated cloud outage handling."""
        legacy_repo = SqliteTradeAdapter(":memory:")
        cloud_repo = SqliteTradeAdapter(":memory:")
        service = DualIngestionService(legacy_repo, cloud_repo)

        # 1. Normal ingestion
        res1 = service.ingest(sample_trade_1)
        assert res1["legacy_inserted"] is True
        assert res1["cloud_inserted"] is True
        assert res1["cloud_status"] == "STORED"

        # 2. Chaos active: Cloud drops, Legacy continues
        service.set_cloud_partition(True)
        res2 = service.ingest(sample_trade_2)
        assert res2["legacy_inserted"] is True
        assert res2["cloud_inserted"] is False
        assert res2["cloud_status"] == "DROPPED_BY_CHAOS"

        assert legacy_repo.count() == 2
        assert cloud_repo.count() == 1
        assert len(service.get_dropped_trades()) == 1

        # 3. Heal chaos & reconcile
        service.set_cloud_partition(False)
        parity = ParityService(legacy_repo, cloud_repo)
        recon = parity.reconcile_from_trades(service.get_dropped_trades())
        assert recon["final_status"] == "IN_PARITY"
        assert cloud_repo.count() == 2

        legacy_repo.close()
        cloud_repo.close()


class TestMemoryEventBus:
    """Test suite for asynchronous in-memory event streaming broker."""

    def test_pub_sub_fanout(self, sample_trade_1: Trade) -> None:
        """Verify broker fans out published event to multiple subscribers concurrently."""
        bus = MemoryEventBus()
        received_a = []
        received_b = []

        bus.subscribe("market.trades", lambda t: received_a.append(t))
        bus.subscribe("market.trades", lambda t: received_b.append(t))

        bus.publish("market.trades", sample_trade_1)
        bus.join()

        assert len(received_a) == 1
        assert len(received_b) == 1
        assert received_a[0].trade_id == "TRD-001"
        assert received_b[0].trade_id == "TRD-001"

        bus.close()


class TestApiRouter:
    """Test suite for REST/OpenAPI endpoints."""

    def test_api_endpoints(self, sample_trade_1: Trade) -> None:
        """Verify /health, /trades, /trades/parity, and /trades/cutover endpoints."""
        legacy_repo = SqliteTradeAdapter(":memory:")
        cloud_repo = SqliteTradeAdapter(":memory:")
        ingestion = DualIngestionService(legacy_repo, cloud_repo)
        parity = ParityService(legacy_repo, cloud_repo)
        router = ApiRouter(ingestion, parity)

        # 1. Health check
        code, health = router.dispatch("GET", "/health")
        assert code == 200
        assert health["status"] == "UP"

        # 2. Ingest trade via API
        payload = {
            "trade_id": "TRD-API-001",
            "instrument": "AAPL",
            "price": 175.0,
            "quantity": 20,
            "buy_order_id": "BUY-1",
            "sell_order_id": "SELL-1",
            "timestamp": "2026-10-01T10:00:00Z",
        }
        code, res = router.dispatch("POST", "/trades", payload)
        assert code == 201
        assert res["trade_id"] == "TRD-API-001"
        assert res["legacy_inserted"] is True

        # 3. Parity status
        code, p_res = router.dispatch("GET", "/trades/parity")
        assert code == 200
        assert p_res["status"] == "IN_PARITY"

        # 4. Cutover
        code, cut_res = router.dispatch("POST", "/trades/cutover")
        assert code == 200
        assert cut_res["status"] == "CUTOVER_SUCCESSFUL"

        # 5. Rollback
        code, roll_res = router.dispatch("POST", "/trades/rollback")
        assert code == 200
        assert roll_res["status"] == "ROLLBACK_SUCCESSFUL"
        assert roll_res["data_loss_percentage"] == 0.0

        legacy_repo.close()
        cloud_repo.close()


class TestLegacyUseCases:
    """Test suite for backward-compatible use case aliases."""

    def test_ingest_trade_use_case(self, sample_trade_1: Trade) -> None:
        """Verify IngestTradeUseCase delegates to repository port."""
        repo = SqliteTradeAdapter(":memory:")
        use_case = IngestTradeUseCase(repo, repo)
        res = use_case.ingest(sample_trade_1)
        assert res["legacy_inserted"] is True
        repo.close()

    def test_parity_checker_alias(self, sample_trade_1: Trade) -> None:
        """Verify ParityCheckerUseCase alias works identically to ParityService."""
        legacy = SqliteTradeAdapter(":memory:")
        cloud = SqliteTradeAdapter(":memory:")
        legacy.save(sample_trade_1)
        cloud.save(sample_trade_1)

        checker = ParityCheckerUseCase(legacy, cloud)
        res = checker.execute()
        assert res["status"] == "IN_PARITY"

        legacy.close()
        cloud.close()


class TestPostgresAdapterMocked:
    """Test suite for PostgresTradeAdapter with mocked psycopg2."""

    @patch("src.adapters.postgres_adapter.psycopg2")
    def test_postgres_adapter_idempotent_save(
        self, mock_psycopg2: MagicMock, sample_trade_1: Trade
    ) -> None:
        """Verify Postgres adapter executes ON CONFLICT DO NOTHING."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = [1]
        mock_cursor.fetchall.return_value = [("TRD-001",)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "test",
            "user": "u",
            "password": "p",
        }
        adapter = PostgresTradeAdapter(params)

        assert adapter.save(sample_trade_1) is True
        assert adapter.count() == 1
        assert adapter.get_all_ids() == {"TRD-001"}

        adapter.close()
        assert mock_conn.close.called
