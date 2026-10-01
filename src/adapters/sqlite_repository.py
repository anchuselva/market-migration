"""SQLite adapter implementing TradeRepository port."""
import sqlite3
import threading
from typing import Set

from src.domain.models import Trade
from src.ports.trade_repository import TradeRepository


class SqliteTradeRepository(TradeRepository):
    """Thread-safe SQLite implementation of TradeRepository.

    Ensures zero duplicate trade ingestion using primary key constraints
    and idempotent INSERT OR IGNORE statements.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize SQLite database connection and verify table schema.

        Args:
            db_path: Path to SQLite database file or ':memory:'.
        """
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode handled via explicit transactions
        )
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the trades table and indexes if not already present."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    instrument TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    buy_order_id TEXT NOT NULL,
                    sell_order_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);"
            )

    def save(self, trade: Trade) -> bool:
        """Persist a trade record idempotently via INSERT OR IGNORE.

        Args:
            trade: The trade entity to store.

        Returns:
            bool: True if inserted, False if ignored due to existing trade_id.
        """
        sql = """
            INSERT OR IGNORE INTO trades (
                trade_id, instrument, price, quantity, buy_order_id, sell_order_id, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                sql,
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
        """Retrieve count of stored trades.

        Returns:
            int: Total trade count.
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades;")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def total_volume(self) -> float:
        """Calculate cumulative traded volume.

        Returns:
            float: Total notional volume (price * quantity).
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COALESCE(SUM(price * quantity), 0.0) FROM trades;")
            row = cursor.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0

    def get_all_ids(self) -> Set[str]:
        """Fetch all unique trade IDs for out-of-band parity comparison.

        Returns:
            Set[str]: Set of trade IDs.
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT trade_id FROM trades;")
            rows = cursor.fetchall()
            return {str(row[0]) for row in rows}

    def close(self) -> None:
        """Safely close database connection."""
        with self._lock:
            self._conn.close()


# Alias to satisfy alternate naming conventions
SQLiteRepository = SqliteTradeRepository
