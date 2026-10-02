"""Unit and integration tests for MysqlTradeAdapter."""
import pytest
from src.domain.models import Trade

try:
    import pymysql
    from src.adapters.mysql_adapter import MysqlTradeAdapter
    # Test connection
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password="", connect_timeout=1)
    conn.close()
    MYSQL_AVAILABLE = True
except Exception:
    MYSQL_AVAILABLE = False


@pytest.mark.skipif(not MYSQL_AVAILABLE, reason="Local XAMPP MySQL server not reachable")
def test_mysql_adapter_lifecycle():
    """Verify idempotent storage and parity queries with MysqlTradeAdapter."""
    adapter = MysqlTradeAdapter(db_name="nexus_test_db")
    adapter.clear()

    trade1 = Trade(
        trade_id="TRD-MYSQL-001",
        instrument="NVDA",
        price=125.50,
        quantity=100,
        buy_order_id="BUY-01",
        sell_order_id="SELL-01",
        timestamp="2026-10-01T10:00:00Z",
    )

    # 1. First save succeeds
    assert adapter.save(trade1) is True
    assert adapter.count() == 1
    assert adapter.total_volume() == 12550.0

    # 2. Duplicate save is ignored (idempotency)
    assert adapter.save(trade1) is False
    assert adapter.count() == 1

    # 3. Second trade
    trade2 = Trade(
        trade_id="TRD-MYSQL-002",
        instrument="AAPL",
        price=220.00,
        quantity=50,
        buy_order_id="BUY-02",
        sell_order_id="SELL-02",
        timestamp="2026-10-01T10:01:00Z",
    )
    assert adapter.save(trade2) is True
    assert adapter.count() == 2
    assert adapter.total_volume() == 12550.0 + (220.00 * 50)
    assert adapter.get_all_ids() == {"TRD-MYSQL-001", "TRD-MYSQL-002"}

    # Cleanup
    adapter.clear()
    assert adapter.count() == 0
