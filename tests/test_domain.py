"""Unit tests for pure financial domain entities and invariants."""
import pytest

from src.domain.exceptions import (
    DomainException,
    InvalidPriceError,
    InvalidQuantityError,
    ValidationError,
)
from src.domain.models import Instrument, Order, Trade


class TestTradeDomainModel:
    """Test suite for Trade domain entity and financial invariant validation."""

    def test_valid_trade_creation(self) -> None:
        """Verify Trade instantiates correctly with valid parameters."""
        trade = Trade(
            trade_id="TRD-1001",
            instrument="AAPL",
            price=150.50,
            quantity=10,
            buy_order_id="BUY-001",
            sell_order_id="SELL-002",
            timestamp="2026-10-01T10:00:00Z",
        )
        assert trade.trade_id == "TRD-1001"
        assert trade.instrument == "AAPL"
        assert trade.price == 150.50
        assert trade.quantity == 10
        assert trade.buy_order_id == "BUY-001"
        assert trade.sell_order_id == "SELL-002"
        assert trade.timestamp == "2026-10-01T10:00:00Z"

    def test_volume_calculation(self) -> None:
        """Verify dollar_volume and volume compute accurate notional cash value."""
        trade = Trade(
            trade_id="TRD-1002",
            instrument="NVDA",
            price=120.0,
            quantity=50,
            buy_order_id="BUY-003",
            sell_order_id="SELL-004",
            timestamp="2026-10-01T10:01:00Z",
        )
        assert trade.dollar_volume() == 6000.0
        assert trade.volume() == 6000.0

    @pytest.mark.parametrize("invalid_price", [0.0, -1.0, -99.99])
    def test_rejects_non_positive_price(self, invalid_price: float) -> None:
        """Ensure ValueError is raised if price is zero or negative."""
        with pytest.raises(ValueError, match="Trade price must be strictly positive"):
            Trade(
                trade_id="TRD-ERR-PRICE",
                instrument="MSFT",
                price=invalid_price,
                quantity=10,
                buy_order_id="BUY-005",
                sell_order_id="SELL-006",
                timestamp="2026-10-01T10:02:00Z",
            )

    @pytest.mark.parametrize("invalid_quantity", [0, -1, -500])
    def test_rejects_non_positive_quantity(self, invalid_quantity: int) -> None:
        """Ensure ValueError is raised if quantity is zero or negative."""
        with pytest.raises(ValueError, match="Trade quantity must be strictly positive"):
            Trade(
                trade_id="TRD-ERR-QTY",
                instrument="GOOGL",
                price=180.0,
                quantity=invalid_quantity,
                buy_order_id="BUY-007",
                sell_order_id="SELL-008",
                timestamp="2026-10-01T10:03:00Z",
            )

    @pytest.mark.parametrize(
        "empty_field",
        ["trade_id", "instrument", "buy_order_id", "sell_order_id", "timestamp"],
    )
    def test_rejects_empty_string_fields(self, empty_field: str) -> None:
        """Ensure all string identifiers are validated to be non-empty."""
        kwargs = {
            "trade_id": "TRD-OK",
            "instrument": "TSLA",
            "price": 250.0,
            "quantity": 5,
            "buy_order_id": "BUY-009",
            "sell_order_id": "SELL-010",
            "timestamp": "2026-10-01T10:04:00Z",
        }
        kwargs[empty_field] = "   "
        with pytest.raises(ValueError, match=f"{empty_field} must be a non-empty string"):
            Trade(**kwargs)

    def test_trade_is_immutable(self) -> None:
        """Ensure Trade cannot be mutated after creation (frozen dataclass)."""
        trade = Trade(
            trade_id="TRD-IMMUTABLE",
            instrument="AMZN",
            price=175.0,
            quantity=20,
            buy_order_id="BUY-011",
            sell_order_id="SELL-012",
            timestamp="2026-10-01T10:05:00Z",
        )
        with pytest.raises(Exception):
            trade.price = 200.0  # type: ignore


class TestOrderDomainModel:
    """Test suite for Order entity and invariant checks."""

    def test_valid_order_creation(self) -> None:
        """Verify Order creation and notional value calculation."""
        order = Order(
            order_id="ORD-101",
            side="BUY",
            instrument="AAPL",
            price=150.0,
            quantity=20,
            timestamp="2026-10-01T10:00:00Z",
        )
        assert order.order_id == "ORD-101"
        assert order.side == "BUY"
        assert order.notional_value() == 3000.0

    def test_order_side_validation(self) -> None:
        """Verify only BUY and SELL are accepted."""
        with pytest.raises(ValueError, match="side must be 'BUY' or 'SELL'"):
            Order(
                order_id="ORD-BAD",
                side="HOLD",
                instrument="AAPL",
                price=150.0,
                quantity=10,
                timestamp="2026-10-01T10:00:00Z",
            )


class TestInstrumentDomainModel:
    """Test suite for Instrument entity."""

    def test_valid_instrument_creation(self) -> None:
        """Verify Instrument initialization with attributes."""
        inst = Instrument(symbol="AAPL", name="Apple Inc.", asset_class="EQUITY")
        assert inst.symbol == "AAPL"
        assert inst.tick_size == 0.01
        assert inst.lot_size == 1

    def test_invalid_tick_size(self) -> None:
        """Verify tick_size must be positive."""
        with pytest.raises(ValueError, match="tick_size must be strictly positive"):
            Instrument(symbol="AAPL", name="Apple Inc.", asset_class="EQUITY", tick_size=0.0)


class TestDomainExceptions:
    """Test suite for domain exception hierarchy."""

    def test_domain_exception_hierarchy(self) -> None:
        """Verify inheritance relationships among domain exceptions."""
        assert issubclass(ValidationError, DomainException)
        assert issubclass(InvalidPriceError, ValidationError)
        assert issubclass(InvalidQuantityError, ValidationError)
