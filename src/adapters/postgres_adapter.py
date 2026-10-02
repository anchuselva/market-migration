"""PostgreSQL / AWS Aurora adapter implementing TradeRepositoryPort."""
import threading
from typing import Any, Dict, Optional, Set

from src.domain.models import Trade
from src.ports.repository_port import TradeRepositoryPort

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None  # type: ignore
    sql = None  # type: ignore


class PostgresTradeAdapter(TradeRepositoryPort):
    """PostgreSQL implementation of TradeRepositoryPort.

    Targets AWS Aurora PostgreSQL compatibility with high throughput and
    idempotent writes via ON CONFLICT (trade_id) DO NOTHING.
    """

    def __init__(self, connection_params: Dict[str, Any]) -> None:
        """Initialize PostgreSQL repository connection.

        Args:
            connection_params: Dictionary with host, port, dbname, user, password.
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is required for PostgresTradeAdapter. "
                "Install it via 'pip install psycopg2-binary'."
            )
        self._params = connection_params
        self._lock = threading.Lock()
        self._conn: Optional[Any] = None
        self._connect()
        self._init_schema()

    def _connect(self) -> None:
        """Establish connection with autocommit for non-blocking single-statement transactions."""
        self._conn = psycopg2.connect(**self._params)
        self._conn.autocommit = True

    def _ensure_connection(self) -> Any:
        """Ensure connection is open, reconnecting if disconnected."""
        if self._conn is None or self._conn.closed != 0:
            self._connect()
        return self._conn

    def _init_schema(self) -> None:
        """Initialize the trades table and indexes if not present."""
        ddl = """
            CREATE TABLE IF NOT EXISTS trades (
                trade_id VARCHAR(64) PRIMARY KEY,
                instrument VARCHAR(32) NOT NULL,
                price DOUBLE PRECISION NOT NULL CHECK(price > 0),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                buy_order_id VARCHAR(64) NOT NULL,
                sell_order_id VARCHAR(64) NOT NULL,
                timestamp VARCHAR(64) NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
            CREATE INDEX IF NOT EXISTS idx_trades_volume ON trades(price, quantity);
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(ddl)

    def save(self, trade: Trade) -> bool:
        """Idempotently persist trade record using ON CONFLICT DO NOTHING.

        Args:
            trade: Trade entity to persist.

        Returns:
            bool: True if new trade was inserted, False if skipped as duplicate.
        """
        insert_query = """
            INSERT INTO trades (
                trade_id, instrument, price, quantity,
                buy_order_id, sell_order_id, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_id) DO NOTHING;
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    insert_query,
                    (
                        trade.trade_id,
                        trade.instrument,
                        trade.price,
                        trade.quantity,
                        trade.buy_order_id,
                        trade.sell_order_id,
                        trade.timestamp,
                    ),
                )
                return cursor.rowcount > 0

    def count(self) -> int:
        """Query total record count from PostgreSQL."""
        query = "SELECT COUNT(*) FROM trades;"
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def total_volume(self) -> float:
        """Calculate aggregate dollar volume in PostgreSQL."""
        query = "SELECT COALESCE(SUM(price * quantity), 0.0) FROM trades;"
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return float(row[0]) if row else 0.0

    def get_all_ids(self) -> Set[str]:
        """Fetch all stored trade_ids for out-of-band parity reconciliation."""
        query = "SELECT trade_id FROM trades;"
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(query)
                return {row[0] for row in cursor.fetchall()}

    def close(self) -> None:
        """Close PostgreSQL connection pool."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass


# Backward compatibility alias
PostgresTradeRepository = PostgresTradeAdapter
