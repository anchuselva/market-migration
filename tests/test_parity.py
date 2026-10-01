"""Unit and integration tests for parity checking, repository idempotency, and event stream."""
import pytest
from src.adapters.queue_stream import QueueEventStream
from src.adapters.sqlite_repository import SqliteTradeRepository
from src.domain.models import Trade
from src.use_cases.ingest_trade import IngestTradeUseCase
from src.use_cases.parity_checker import ParityCheckerUseCase


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
        repo = SqliteTradeRepository(":memory:")

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
        repo = SqliteTradeRepository(":memory:")
        repo.save(sample_trade_1)
        repo.save(sample_trade_2)

        assert repo.count() == 2
        # (150 * 10) + (200 * 5) = 1500 + 1000 = 2500.0
        assert repo.total_volume() == 2500.0
        assert repo.get_all_ids() == {"TRD-001", "TRD-002"}

        repo.close()


class TestQueueEventStreamFanOut:
    """Test suite for the in-memory event stream broker fan-out pattern."""

    def test_concurrent_fan_out(self, sample_trade_1: Trade) -> None:
        """Ensure published trade is delivered to all registered subscriber queues."""
        stream = QueueEventStream()
        legacy_received: list[Trade] = []
        cloud_received: list[Trade] = []

        stream.subscribe("market.trades", lambda t: legacy_received.append(t))
        stream.subscribe("market.trades", lambda t: cloud_received.append(t))

        stream.publish("market.trades", sample_trade_1)
        stream.join()

        assert len(legacy_received) == 1
        assert len(cloud_received) == 1
        assert legacy_received[0].trade_id == sample_trade_1.trade_id
        assert cloud_received[0].trade_id == sample_trade_1.trade_id

        stream.close()


class TestIngestTradeUseCase:
    """Test suite for IngestTradeUseCase execution."""

    def test_use_case_execution(self, sample_trade_1: Trade) -> None:
        """Verify use case triggers repository save."""
        repo = SqliteTradeRepository(":memory:")
        use_case = IngestTradeUseCase(repo)

        result = use_case.execute(sample_trade_1)
        assert result is True
        assert repo.count() == 1

        # Re-run -> idempotent False
        result_duplicate = use_case.execute(sample_trade_1)
        assert result_duplicate is False
        assert repo.count() == 1

        repo.close()


class TestParityCheckerUseCase:
    """Test suite for ParityCheckerUseCase audit logic and drift detection."""

    def test_parity_in_sync(self, sample_trade_1: Trade, sample_trade_2: Trade) -> None:
        """Verify 'IN_PARITY' status when legacy and cloud have identical records."""
        legacy_repo = SqliteTradeRepository(":memory:")
        cloud_repo = SqliteTradeRepository(":memory:")

        # Populate both identical
        legacy_repo.save(sample_trade_1)
        legacy_repo.save(sample_trade_2)
        cloud_repo.save(sample_trade_1)
        cloud_repo.save(sample_trade_2)

        checker = ParityCheckerUseCase(legacy_repo, cloud_repo)
        report = checker.execute()

        assert report["legacy_count"] == 2
        assert report["cloud_count"] == 2
        assert report["drift"] == 0
        assert report["status"] == "IN_PARITY"
        assert report["volume_difference"] == 0.0
        assert checker.get_missing_cloud_ids() == set()

        legacy_repo.close()
        cloud_repo.close()

    def test_parity_drift_detected_and_recovery(
        self, sample_trade_1: Trade, sample_trade_2: Trade
    ) -> None:
        """Verify drift detection when cloud misses a trade and recovery restores parity."""
        legacy_repo = SqliteTradeRepository(":memory:")
        cloud_repo = SqliteTradeRepository(":memory:")

        # Legacy receives both, cloud receives only trade 1 (simulating network partition)
        legacy_repo.save(sample_trade_1)
        legacy_repo.save(sample_trade_2)
        cloud_repo.save(sample_trade_1)

        checker = ParityCheckerUseCase(legacy_repo, cloud_repo)
        report = checker.execute()

        assert report["legacy_count"] == 2
        assert report["cloud_count"] == 1
        assert report["drift"] == 1
        assert report["status"] == "DRIFT_DETECTED"
        assert report["volume_difference"] == sample_trade_2.volume()

        missing = checker.get_missing_cloud_ids()
        assert missing == {"TRD-002"}

        # Simulate Failback / Replay recovery: ingest missing trade to cloud
        cloud_repo.save(sample_trade_2)

        recovered_report = checker.execute()
        assert recovered_report["legacy_count"] == 2
        assert recovered_report["cloud_count"] == 2
        assert recovered_report["drift"] == 0
        assert recovered_report["status"] == "IN_PARITY"
        assert recovered_report["volume_difference"] == 0.0

        legacy_repo.close()
        cloud_repo.close()


class TestPostgresTradeRepositoryMocked:
    """Test suite verifying PostgresTradeRepository logic and queries using mocks."""

    def test_postgres_operations(
        self, monkeypatch: pytest.MonkeyPatch, sample_trade_1: Trade
    ) -> None:
        """Verify PostgresTradeRepository interactions with psycopg2 cursor."""
        from unittest.mock import MagicMock
        from src.adapters.postgres_repository import PostgresTradeRepository

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.closed = 0

        # Mock psycopg2.connect
        import psycopg2
        monkeypatch.setattr(psycopg2, "connect", lambda **kwargs: mock_conn)

        repo = PostgresTradeRepository({"host": "localhost", "port": 5433})

        # Test save - row inserted
        mock_cursor.rowcount = 1
        assert repo.save(sample_trade_1) is True

        # Test save - duplicate ignored (rowcount 0)
        mock_cursor.rowcount = 0
        assert repo.save(sample_trade_1) is False

        # Test count
        mock_cursor.fetchone.return_value = [42]
        assert repo.count() == 42

        # Test total_volume
        mock_cursor.fetchone.return_value = [123456.78]
        assert repo.total_volume() == 123456.78

        # Test get_all_ids
        mock_cursor.fetchall.return_value = [("TRD-001",), ("TRD-002",)]
        assert repo.get_all_ids() == {"TRD-001", "TRD-002"}

        repo.close()
        assert mock_conn.close.called


class TestTradeReportingWorkload:
    """Test suite for the migrated core Trade Reporting workload."""

    def test_trade_reporting_generation(
        self, sample_trade_1: Trade, sample_trade_2: Trade
    ) -> None:
        """Verify regulatory report computes accurate metrics from cloud repository."""
        from src.use_cases.trade_reporting import TradeReportingUseCase

        cloud_repo = SqliteTradeRepository(":memory:")
        cloud_repo.save(sample_trade_1)
        cloud_repo.save(sample_trade_2)

        reporting_use_case = TradeReportingUseCase(cloud_repo)
        report = reporting_use_case.generate_eod_regulatory_report()

        assert report["workload_name"] == "Post-Trade Regulatory Reporting & Surveillance"
        assert report["execution_status"] == "CLOUD_NATIVE_ACTIVE"
        assert report["total_reported_executions"] == 2
        assert report["total_notional_volume"] == 2500.0
        assert report["average_execution_value"] == 1250.0

        cloud_repo.close()
