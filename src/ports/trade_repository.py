"""Trade repository port interface."""
from abc import ABC, abstractmethod
from typing import Set

from src.domain.models import Trade


class TradeRepository(ABC):
    """Abstract Port for trade persistence repositories.

    Decouples domain and use-case layers from concrete database implementations.
    """

    @abstractmethod
    def save(self, trade: Trade) -> bool:
        """Persist a trade record idempotently.

        Args:
            trade: The trade entity to store.

        Returns:
            bool: True if a new trade was inserted, False if it was ignored (duplicate).
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
        """Calculate the aggregate notional volume of all stored trades.

        Returns:
            float: Cumulative trade volume.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_ids(self) -> Set[str]:
        """Fetch all unique trade IDs currently in the repository.

        Returns:
            Set[str]: Set of trade IDs for out-of-band parity reconciliation.
        """
        raise NotImplementedError
