"""MySQL / MariaDB Trade Repository Adapter for XAMPP and Cloud Environments.

Implements TradeRepositoryPort using PyMySQL with idempotent INSERT IGNORE semantics.
"""
import threading
from typing import Set

try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

from src.domain.models import Trade
from src.ports.repository_port import TradeRepositoryPort


class MysqlTradeAdapter(TradeRepositoryPort):
    """MySQL / MariaDB persistent trade repository adapter.

    Enforces idempotent writes using INSERT IGNORE to prevent duplicate
    key collisions during catch-up reconciliation.
    """

    def __init__(
        self,
        db_name: str = "nexus_legacy_db",
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
    ) -> None:
        """Initialize connection parameters and create tables if absent."""
        if not HAS_PYMYSQL:
            raise ImportError(
                "PyMySQL is required for MysqlTradeAdapter. Run 'pip install pymysql'."
            )

        self.db_name = db_name
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.lock = threading.Lock()

        self._ensure_database_and_table()

    def _get_connection(self) -> "pymysql.Connection":
        """Open a new connection to the MySQL database."""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db_name,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _ensure_database_and_table(self) -> None:
        """Ensure target schema and trades table exist."""
        # Connect to root server to ensure database exists
        root_conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            autocommit=True,
        )
        try:
            with root_conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`;")
        finally:
            root_conn.close()

        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id VARCHAR(64) PRIMARY KEY,
                        instrument VARCHAR(32) NOT NULL,
                        price DECIMAL(15, 2) NOT NULL,
                        quantity INT NOT NULL,
                        buy_order_id VARCHAR(64) NOT NULL,
                        sell_order_id VARCHAR(64) NOT NULL,
                        timestamp VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
        finally:
            conn.close()

    def save(self, trade: Trade) -> bool:
        """Persist a trade record idempotently via INSERT IGNORE."""
        query = """
            INSERT IGNORE INTO trades
            (trade_id, instrument, price, quantity, buy_order_id, sell_order_id, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                affected = cursor.execute(
                    query,
                    (
                        trade.trade_id,
                        trade.instrument,
                        float(trade.price),
                        int(trade.quantity),
                        trade.buy_order_id,
                        trade.sell_order_id,
                        trade.timestamp,
                    ),
                )
                return affected > 0
        finally:
            conn.close()

    def count(self) -> int:
        """Retrieve total trade count."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM trades")
                row = cursor.fetchone()
                return int(row["total"]) if row else 0
        finally:
            conn.close()

    def total_volume(self) -> float:
        """Calculate aggregate dollar volume."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(SUM(price * quantity), 0) AS total_vol FROM trades")
                row = cursor.fetchone()
                return float(row["total_vol"]) if row else 0.0
        finally:
            conn.close()

    def get_all_ids(self) -> Set[str]:
        """Fetch all unique trade IDs."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT trade_id FROM trades")
                rows = cursor.fetchall()
                return {row["trade_id"] for row in rows}
        finally:
            conn.close()

    def clear(self) -> None:
        """Truncate all records for test suite or reset."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE trades")
        finally:
            conn.close()

    def close(self) -> None:
        """Close resources (no persistent pool in this implementation)."""
        pass
