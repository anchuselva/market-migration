"""Application configuration settings for hybrid cloud migration."""
import os
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class DatabaseSettings:
    """Database connectivity parameters."""

    legacy_sqlite_path: str = "legacy_trades.db"
    cloud_sqlite_path: str = "cloud_trades.db"

    # PostgreSQL configuration (local Docker Compose or AWS Aurora)
    legacy_pg_host: str = os.getenv("LEGACY_PG_HOST", "localhost")
    legacy_pg_port: int = int(os.getenv("LEGACY_PG_PORT", "5432"))
    legacy_pg_db: str = os.getenv("LEGACY_PG_DB", "legacy_trading")
    legacy_pg_user: str = os.getenv("LEGACY_PG_USER", "postgres")
    legacy_pg_password: str = os.getenv("LEGACY_PG_PASSWORD", "password123")

    cloud_pg_host: str = os.getenv("CLOUD_PG_HOST", "localhost")
    cloud_pg_port: int = int(os.getenv("CLOUD_PG_PORT", "5433"))
    cloud_pg_db: str = os.getenv("CLOUD_PG_DB", "cloud_trading")
    cloud_pg_user: str = os.getenv("CLOUD_PG_USER", "postgres")
    cloud_pg_password: str = os.getenv("CLOUD_PG_PASSWORD", "password123")

    def legacy_pg_params(self) -> Dict[str, Any]:
        """Return connection dictionary for legacy PostgreSQL."""
        return {
            "host": self.legacy_pg_host,
            "port": self.legacy_pg_port,
            "dbname": self.legacy_pg_db,
            "user": self.legacy_pg_user,
            "password": self.legacy_pg_password,
        }

    def cloud_pg_params(self) -> Dict[str, Any]:
        """Return connection dictionary for cloud PostgreSQL (Aurora)."""
        return {
            "host": self.cloud_pg_host,
            "port": self.cloud_pg_port,
            "dbname": self.cloud_pg_db,
            "user": self.cloud_pg_user,
            "password": self.cloud_pg_password,
        }


@dataclass
class StreamSettings:
    """Event broker settings."""

    trade_topic: str = "market.trades"
    consumer_batch_size: int = 50
    reconciliation_interval_sec: float = 0.5


@dataclass
class Settings:
    """Master application configuration."""

    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    stream: StreamSettings = field(default_factory=StreamSettings)
    raw_data_path: str = os.path.join("data", "raw_trades.csv")
    cleaned_data_path: str = os.path.join("data", "cleaned_trades.csv")


def get_settings() -> Settings:
    """Retrieve application settings instance."""
    return Settings()
