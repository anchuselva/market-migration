"""Trade repository port interface.

Decouples domain models and use cases from database infrastructure.
"""
from abc import ABC, abstractmethod
from typing import Set

from src.domain.models import Trade


class TradeRepositoryPort(ABC):
    """Abstract Port for trade persistence repositories.

    Defines the contract for storing and querying trade execution data
    across heterogeneous databases (SQLite, PostgreSQL, AWS Aurora).
    """

    @abstractmethod
    def save(self, trade: Trade) -> bool:
        """Persist a trade record idempotently.

        Args:
            trade: The trade domain entity to store.

        Returns:
            bool: True if a new trade was inserted, False if skipped as duplicate.
        """
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Retrieve the total count of distinct trades stored.

        Returns:
            int: Total trade count.
        """
        raise NotImplementedError

    @abstractmethod
    def total_volume(self) -> float:
        """Calculate the aggregate dollar volume of all stored trades.

        Returns:
            float: Cumulative notional trade volume.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_ids(self) -> Set[str]:
        """Fetch all unique trade IDs currently in the repository.

        Returns:
            Set[str]: Set of trade IDs for out-of-band parity reconciliation.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Gracefully release database connections and pool resources."""
        pass


# Backward compatibility alias
TradeRepository = TradeRepositoryPort
