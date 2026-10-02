"""PostgreSQL adapter re-export for backward compatibility."""
from src.adapters.postgres_adapter import PostgresTradeAdapter, PostgresTradeRepository

__all__ = ["PostgresTradeAdapter", "PostgresTradeRepository"]
