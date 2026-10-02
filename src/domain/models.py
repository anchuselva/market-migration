"""Pure domain entities for financial exchange trade processing.

Adheres strictly to Clean Architecture / Hexagonal Architecture with zero
framework or infrastructure dependencies.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Instrument:
    """Pure domain entity representing a financial instrument / traded asset."""

    symbol: str
    name: str
    asset_class: str
    tick_size: float = 0.01
    lot_size: int = 1

    def __post_init__(self) -> None:
        """Validate instrument invariants."""
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if self.tick_size <= 0:
            raise ValueError(f"tick_size must be strictly positive, got: {self.tick_size}")
        if self.lot_size <= 0:
            raise ValueError(f"lot_size must be strictly positive, got: {self.lot_size}")


@dataclass(frozen=True)
class Order:
    """Pure domain entity representing an order submitted to the matching engine."""

    order_id: str
    side: str  # "BUY" or "SELL"
    instrument: str
    price: float
    quantity: int
    timestamp: str
    account_id: Optional[str] = None
    status: str = "FILLED"

    def __post_init__(self) -> None:
        """Validate order invariants."""
        if not isinstance(self.order_id, str) or not self.order_id.strip():
            raise ValueError("order_id must be a non-empty string")
        if self.side.upper() not in {"BUY", "SELL"}:
            raise ValueError(f"side must be 'BUY' or 'SELL', got: {self.side}")
        if not isinstance(self.instrument, str) or not self.instrument.strip():
            raise ValueError("instrument must be a non-empty string")
        if self.price <= 0.0:
            raise ValueError(f"Order price must be strictly positive (> 0), got: {self.price}")
        if self.quantity <= 0:
            raise ValueError(
                f"Order quantity must be strictly positive (> 0), got: {self.quantity}"
            )
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("timestamp must be a non-empty string")

    def notional_value(self) -> float:
        """Calculate notional cash value of the order."""
        return float(self.price * self.quantity)


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

    def dollar_volume(self) -> float:
        """Calculate total notional cash volume of the trade.

        Returns:
            float: Total trade value (price * quantity).
        """
        return float(self.price * self.quantity)

    def volume(self) -> float:
        """Backward-compatible alias for dollar_volume.

        Returns:
            float: Total trade value (price * quantity).
        """
        return self.dollar_volume()
