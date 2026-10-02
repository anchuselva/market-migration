"""Event bus port interface.

Decouples event streaming brokers (Kafka, RabbitMQ, MemoryBus) from business logic.
"""
from abc import ABC, abstractmethod
from typing import Callable

from src.domain.models import Trade


class EventBusPort(ABC):
    """Abstract Port for asynchronous publish/subscribe event distribution.

    Enables non-blocking streaming of market trades to dual shadow consumers.
    """

    @abstractmethod
    def publish(self, topic: str, payload: Trade) -> None:
        """Publish a trade event payload to the specified topic.

        Args:
            topic: The destination topic name (e.g. 'market.trades').
            payload: The trade domain entity to broadcast.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[Trade], None]) -> None:
        """Register a subscriber callback for events on the specified topic.

        Args:
            topic: The topic name to monitor.
            callback: Callable invoked asynchronously with each received trade.
        """
        raise NotImplementedError

    def join(self) -> None:
        """Wait for all published events to be consumed and processed."""
        pass

    def close(self) -> None:
        """Terminate all worker threads and consumer queues cleanly."""
        pass


# Backward compatibility alias
EventStream = EventBusPort
