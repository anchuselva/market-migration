"""Use case for executing trade ingestion into a repository."""
from src.domain.models import Trade
from src.ports.repository_port import TradeRepositoryPort


class IngestTradeUseCase:
    """Orchestrates the ingestion and persistence of a trade into a target repository."""

    def __init__(self, repository: TradeRepositoryPort) -> None:
        """Initialize use case with a concrete TradeRepositoryPort.

        Args:
            repository: An instance implementing TradeRepositoryPort.
        """
        self._repository = repository

    def execute(self, trade: Trade) -> bool:
        """Execute trade persistence with idempotency guarantee.

        Args:
            trade: The trade entity to ingest.

        Returns:
            bool: True if trade was newly recorded, False if already present (idempotent skip).
        """
        return self._repository.save(trade)
