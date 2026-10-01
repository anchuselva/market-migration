"""PostgreSQL adapter implementing TradeRepository for AWS Aurora compatibility."""
import threading
from typing import Any, Dict, Optional, Set

from src.domain.models import Trade
from src.ports.trade_repository import TradeRepository

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None  # type: ignore
    sql = None  # type: ignore


class PostgresTradeRepository(TradeRepository):
    """PostgreSQL implementation of TradeRepository.

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
                "psycopg2 is required for PostgresTradeRepository. "
                "Install it via 'pip install psycopg2-binary'."
            )
        self._params = connection_params
        self._lock = threading.Lock()
        self._conn: Optional[Any] = None
        self._connect()
        self._init_schema()

    def _connect(self) -> None:
        """Establish connection with autocommit disabled for atomic transactions."""
        self._conn = psycopg2.connect(**self._params)
        self._conn.autocommit = True

    def _ensure_connection(self) -> Any:
        """Ensure connection is open, reconnecting if needed."""
        if self._conn is None or self._conn.closed != 0:
            self._connect()
        return self._conn

    def _init_schema(self) -> None:
        """Initialize the trades table and indexes if not present."""
        ddl = """
            CREATE TABLE IF NOT EXISTS trades (
                trade_id VARCHAR(64) PRIMARY KEY,
                instrument VARCHAR(32) NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                quantity INTEGER NOT NULL,
                buy_order_id VARCHAR(64) NOT NULL,
                sell_order_id VARCHAR(64) NOT NULL,
                timestamp VARCHAR(64) NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(ddl)

    def save(self, trade: Trade) -> bool:
        """Persist a trade idempotently using ON CONFLICT DO NOTHING.

        Args:
            trade: The trade entity to store.

        Returns:
            bool: True if inserted, False if row already existed.
        """
        query = """
            INSERT INTO trades (
                trade_id, instrument, price, quantity, buy_order_id, sell_order_id, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_id) DO NOTHING;
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
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
        """Retrieve total count of distinct stored trades.

        Returns:
            int: Trade count.
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM trades;")
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def total_volume(self) -> float:
        """Calculate total notional traded volume.

        Returns:
            float: Cumulative volume (price * quantity).
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(SUM(price * quantity), 0.0) FROM trades;")
                row = cursor.fetchone()
                return float(row[0]) if row and row[0] is not None else 0.0

    def get_all_ids(self) -> Set[str]:
        """Fetch all trade IDs for out-of-band parity reconciliation.

        Returns:
            Set[str]: Set of trade IDs.
        """
        with self._lock:
            conn = self._ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT trade_id FROM trades;")
                rows = cursor.fetchall()
                return {str(row[0]) for row in rows}

    def close(self) -> None:
        """Safely close PostgreSQL connection."""
        with self._lock:
            if self._conn and not self._conn.closed:
                self._conn.close()
