"""Event stream port interface."""
from abc import ABC, abstractmethod
from typing import Callable

from src.domain.models import Trade


class EventStream(ABC):
    """Abstract Port for asynchronous publish/subscribe event distribution.

    Decouples message brokers (Kafka, RabbitMQ, in-memory queues) from processing logic.
    """

    @abstractmethod
    def publish(self, topic: str, trade: Trade) -> None:
        """Publish a trade event to the specified topic.

        Args:
            topic: The destination topic name (e.g., 'market.trades').
            trade: The trade entity to broadcast.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[Trade], None]) -> None:
        """Register a subscriber callback for events on the specified topic.

        Args:
            topic: The topic name to monitor.
            callback: Callable invoked synchronously or asynchronously with each received trade.
        """
        raise NotImplementedError
