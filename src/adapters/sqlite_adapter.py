"""SQLite adapter implementing TradeRepositoryPort."""
import sqlite3
import threading
from typing import Optional, Set

from src.domain.models import Trade
from src.ports.repository_port import TradeRepositoryPort


class SqliteTradeAdapter(TradeRepositoryPort):
    """Thread-safe SQLite implementation of TradeRepositoryPort.

    Guarantees zero-duplicate trade ingestion via PRIMARY KEY constraints
    and idempotent INSERT OR IGNORE operations.
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
            isolation_level=None,
        )
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the trades table and performance indexes."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    instrument TEXT NOT NULL,
                    price REAL NOT NULL CHECK(price > 0),
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
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
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_vol ON trades(price, quantity);"
            )

    def clear(self) -> None:
        """Clear all records from trades table."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM trades;")

    def save(self, trade: Trade) -> bool:
        """Persist a trade record idempotently via INSERT OR IGNORE.

        Args:
            trade: Trade entity to save.

        Returns:
            bool: True if inserted as a new record; False if skipped as duplicate.
        """
        sql = """
            INSERT OR IGNORE INTO trades (
                trade_id, instrument, price, quantity,
                buy_order_id, sell_order_id, timestamp
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
        """Count total distinct trades stored."""
        sql = "SELECT COUNT(*) FROM trades;"
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def total_volume(self) -> float:
        """Compute aggregate dollar volume of all stored trades."""
        sql = "SELECT COALESCE(SUM(price * quantity), 0.0) FROM trades;"
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            return float(row[0]) if row else 0.0

    def get_all_ids(self) -> Set[str]:
        """Fetch set of all unique trade IDs currently in the repository."""
        sql = "SELECT trade_id FROM trades;"
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            return {row[0] for row in cursor.fetchall()}

    def find_by_id(self, trade_id: str) -> Optional[Trade]:
        """Retrieve a specific trade by trade_id."""
        sql = """
            SELECT trade_id, instrument, price, quantity, buy_order_id, sell_order_id, timestamp
            FROM trades WHERE trade_id = ?;
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(sql, (trade_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Trade(
                trade_id=row[0],
                instrument=row[1],
                price=float(row[2]),
                quantity=int(row[3]),
                buy_order_id=row[4],
                sell_order_id=row[5],
                timestamp=row[6],
            )

    def close(self) -> None:
        """Close SQLite database connection."""
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass


# Backward compatibility alias
SqliteTradeRepository = SqliteTradeAdapter
