"""Asynchronous decoupled in-memory message broker simulating Apache Kafka."""
import queue
import threading
from typing import Callable, Dict, List, Optional

from src.domain.models import Trade
from src.ports.event_bus_port import EventBusPort


class MemoryEventBus(EventBusPort):
    """Thread-safe in-memory publish/subscribe broker using Python queue.Queue.

    Simulates high-throughput Apache Kafka topic fan-out with independent,
    isolated consumer group queues for decoupled parallel dual-ingestion.
    """

    def __init__(self) -> None:
        """Initialize topic registries, worker tracking, and thread locks."""
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[queue.Queue[Optional[Trade]]]] = {}
        self._threads: List[threading.Thread] = []
        self._running = True

    def subscribe(self, topic: str, callback: Callable[[Trade], None]) -> None:
        """Register a subscriber callback for a specific event topic.

        Spawns a dedicated background consumer worker thread with its own
        independent FIFO queue, preventing slow consumers from blocking others.

        Args:
            topic: Topic identifier (e.g. 'market.trades').
            callback: Consumer function to execute when a trade arrives.
        """
        subscriber_queue: queue.Queue[Optional[Trade]] = queue.Queue()

        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(subscriber_queue)

        def _consumer_worker() -> None:
            while self._running:
                try:
                    trade = subscriber_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if trade is None:
                    subscriber_queue.task_done()
                    break

                try:
                    callback(trade)
                except Exception:
                    # In production, route poison pills to Dead Letter Queue (DLQ)
                    pass
                finally:
                    subscriber_queue.task_done()

        thread = threading.Thread(
            target=_consumer_worker,
            name=f"ConsumerWorker-{topic}-{len(self._subscribers[topic])}",
            daemon=True,
        )
        self._threads.append(thread)
        thread.start()

    def publish(self, topic: str, payload: Trade) -> None:
        """Publish a trade event payload to all topic subscribers asynchronously.

        Args:
            topic: Destination topic.
            payload: Trade domain entity.
        """
        with self._lock:
            queues = list(self._subscribers.get(topic, []))

        for q in queues:
            q.put(payload)

    def join(self) -> None:
        """Block until all queues across all topics have completed processing."""
        with self._lock:
            all_queues = [q for queues in self._subscribers.values() for q in queues]

        for q in all_queues:
            q.join()

    def close(self) -> None:
        """Signal termination to all consumer threads and wait for shutdown."""
        self._running = False
        with self._lock:
            for queues in self._subscribers.values():
                for q in queues:
                    q.put(None)

        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=1.0)


# Backward compatibility aliases
MemoryBus = MemoryEventBus
QueueEventStream = MemoryEventBus
