"""Ingestion service for decoupled shadow running dual-stream trade dispatching."""
import threading
from typing import Any, Callable, Dict, List

from src.domain.models import Trade
from src.ports.event_bus_port import EventBusPort
from src.ports.repository_port import TradeRepositoryPort


class DualIngestionService:
    """Coordinates dual-stream trade ingestion across Legacy and Cloud repositories.

    Implements the Decoupled Shadow Running pattern:
    - Legacy Store: Primary on-premise transactional store (Always recorded).
    - Cloud Store: Shadow runner evaluating target database performance and consistency.
    - Chaos Simulation: Simulates transient cloud partition/outage without impacting Legacy.
    """

    def __init__(
        self,
        legacy_repo: TradeRepositoryPort,
        cloud_repo: TradeRepositoryPort,
    ) -> None:
        """Initialize dual ingestion service with repository ports.

        Args:
            legacy_repo: On-premise legacy persistence adapter.
            cloud_repo: Target cloud persistence adapter.
        """
        self._legacy_repo = legacy_repo
        self._cloud_repo = cloud_repo
        self._lock = threading.Lock()

        # Shadow running and chaos control state
        self._cloud_partition_active: bool = False
        self._dropped_trades: List[Trade] = []
        self._cloud_active: bool = True

    @property
    def is_cloud_partition_active(self) -> bool:
        """Check if cloud network partition / chaos mode is active."""
        with self._lock:
            return self._cloud_partition_active

    def set_cloud_partition(self, active: bool) -> None:
        """Activate or clear simulated cloud partition / network failure.

        Args:
            active: True to simulate cloud drop, False to restore cloud ingestion.
        """
        with self._lock:
            self._cloud_partition_active = active

    def set_cloud_active(self, active: bool) -> None:
        """Completely halt cloud worker (for hard failover / rollback drills)."""
        with self._lock:
            self._cloud_active = active

    def get_dropped_trades(self) -> List[Trade]:
        """Retrieve copy of trades dropped during simulated cloud partition."""
        with self._lock:
            return list(self._dropped_trades)

    def clear_dropped_trades(self) -> None:
        """Reset the buffer of dropped trades."""
        with self._lock:
            self._dropped_trades.clear()

    def ingest(self, trade: Trade) -> Dict[str, Any]:
        """Ingest a trade domain entity into both stores with shadow semantics.

        Args:
            trade: Pristine Trade domain model.

        Returns:
            Dict[str, Any]: Result map indicating legacy and cloud insertion statuses.
        """
        # 1. Primary Ingestion: Legacy On-Prem (Always executed)
        legacy_inserted = self._legacy_repo.save(trade)

        # 2. Shadow Ingestion: Cloud Target
        cloud_inserted = False
        cloud_status = "STORED"

        with self._lock:
            if not self._cloud_active:
                cloud_status = "HALTED"
            elif self._cloud_partition_active:
                cloud_status = "DROPPED_BY_CHAOS"
                self._dropped_trades.append(trade)
            else:
                cloud_inserted = self._cloud_repo.save(trade)
                cloud_status = "STORED" if cloud_inserted else "DUPLICATE_SKIPPED"

        return {
            "trade_id": trade.trade_id,
            "legacy_inserted": legacy_inserted,
            "cloud_inserted": cloud_inserted,
            "cloud_status": cloud_status,
        }

    def create_legacy_consumer(self) -> Callable[[Trade], None]:
        """Factory for legacy event bus consumer callback."""
        def _legacy_consumer(trade: Trade) -> None:
            self._legacy_repo.save(trade)
        return _legacy_consumer

    def create_cloud_consumer(self) -> Callable[[Trade], None]:
        """Factory for cloud shadow event bus consumer callback with chaos handling."""
        def _cloud_consumer(trade: Trade) -> None:
            with self._lock:
                if not self._cloud_active:
                    return
                if self._cloud_partition_active:
                    self._dropped_trades.append(trade)
                    return
            self._cloud_repo.save(trade)
        return _cloud_consumer

    def bind_to_event_bus(self, event_bus: EventBusPort, topic: str = "market.trades") -> None:
        """Subscribe dual shadow consumers to an asynchronous event bus topic.

        Args:
            event_bus: EventBusPort instance (e.g. MemoryEventBus).
            topic: Streaming topic name.
        """
        event_bus.subscribe(topic, self.create_legacy_consumer())
        event_bus.subscribe(topic, self.create_cloud_consumer())


# Backward compatibility aliases
IngestTradeUseCase = DualIngestionService
