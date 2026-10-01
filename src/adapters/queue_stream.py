"""In-memory event broker adapter simulating Kafka topic fan-out."""
import queue
import threading
from typing import Callable, Dict, List, Optional

from src.domain.models import Trade
from src.ports.event_stream import EventStream


class QueueEventStream(EventStream):
    """In-memory event stream adapter using Python queue.Queue.

    Simulates high-throughput Apache Kafka pub/sub topic architecture with
    concurrent fan-out to all registered subscribers.
    """

    def __init__(self) -> None:
        """Initialize topic registry and threading state."""
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[queue.Queue[Optional[Trade]]]] = {}
        self._threads: List[threading.Thread] = []
        self._running = True

    def subscribe(self, topic: str, callback: Callable[[Trade], None]) -> None:
        """Register a subscriber callback for a specific topic.

        Spawns a dedicated consumer worker thread with its own independent
        queue to simulate decoupled Kafka consumer group semantics.

        Args:
            topic: The topic name (e.g. 'market.trades').
            callback: Function invoked when a trade is received.
        """
        subscriber_queue: queue.Queue[Optional[Trade]] = queue.Queue()

        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(subscriber_queue)

        def _worker() -> None:
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
                    # In production streaming, log error and send to DLQ
                    pass
                finally:
                    subscriber_queue.task_done()

        thread = threading.Thread(
            target=_worker,
            name=f"Worker-{topic}-{len(self._subscribers[topic])}",
            daemon=True,
        )
        thread.start()
        self._threads.append(thread)

    def publish(self, topic: str, trade: Trade) -> None:
        """Publish a trade event with fan-out to all registered topic subscribers.

        Args:
            topic: The destination topic name.
            trade: The trade entity to broadcast.
        """
        with self._lock:
            queues = list(self._subscribers.get(topic, []))

        for q in queues:
            q.put(trade)

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for all subscriber queues to finish processing pending events."""
        with self._lock:
            all_queues = [
                q for q_list in self._subscribers.values() for q in q_list
            ]
        for q in all_queues:
            q.join()

    def close(self) -> None:
        """Gracefully terminate worker threads and drain queues."""
        self._running = False
        with self._lock:
            all_queues = [
                q for q_list in self._subscribers.values() for q in q_list
            ]
        for q in all_queues:
            q.put(None)
        for thread in self._threads:
            thread.join(timeout=1.0)
