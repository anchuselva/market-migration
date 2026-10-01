"""Domain entities for financial exchange trade processing."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    """Pure domain entity representing an executed financial trade.

    Adheres strictly to Clean Architecture with zero external library dependencies.
    """

    trade_id: str
    instrument: str
    price: float
    quantity: int
    buy_order_id: str
    sell_order_id: str
    timestamp: str

    def __post_init__(self) -> None:
        """Validate financial domain invariants upon trade instantiation."""
        if not isinstance(self.trade_id, str) or not self.trade_id.strip():
            raise ValueError("trade_id must be a non-empty string")
        if not isinstance(self.instrument, str) or not self.instrument.strip():
            raise ValueError("instrument must be a non-empty string")
        if self.price <= 0.0:
            raise ValueError(f"Trade price must be strictly positive (> 0), got: {self.price}")
        if self.quantity <= 0:
            raise ValueError(
                f"Trade quantity must be strictly positive (> 0), got: {self.quantity}"
            )
        if not isinstance(self.buy_order_id, str) or not self.buy_order_id.strip():
            raise ValueError("buy_order_id must be a non-empty string")
        if not isinstance(self.sell_order_id, str) or not self.sell_order_id.strip():
            raise ValueError("sell_order_id must be a non-empty string")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("timestamp must be a non-empty string")

    def volume(self) -> float:
        """Calculate total notional cash volume of the trade.

        Returns:
            float: Total trade value (price * quantity).
        """
        return float(self.price * self.quantity)
