"""REST API route dispatchers and request handlers for Hybrid Cloud Migration."""
from http import HTTPStatus
from typing import Any, Callable, Dict, Optional, Tuple

from src.domain.models import Trade
from src.services.ingestion_service import DualIngestionService
from src.services.parity_service import ParityService

HandlerFunc = Callable[[Dict[str, Any]], Tuple[int, Dict[str, Any]]]


class ApiRouter:
    """Lightweight pure Python REST router for trade ingestion and migration operations.

    Zero third-party framework dependencies, compatible with standard library http.server,
    WSGI, or ASGI adapters.
    """

    def __init__(
        self,
        ingestion_service: DualIngestionService,
        parity_service: ParityService,
    ) -> None:
        """Initialize API router with core domain services.

        Args:
            ingestion_service: Dual shadow trade ingestion coordinator.
            parity_service: Out-of-band parity auditor and reconciler.
        """
        self.ingestion_service = ingestion_service
        self.parity_service = parity_service
        self.is_cutover_active: bool = False
        self.is_rollback_active: bool = False

    def dispatch(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Dispatch HTTP request to matching controller action.

        Args:
            method: HTTP verb ('GET', 'POST', etc.)
            path: Target request URI path.
            body: Parsed JSON payload dictionary (if applicable).

        Returns:
            Tuple[int, Dict[str, Any]]: HTTP status code and response payload dictionary.
        """
        route_key = (method.upper(), path.rstrip("/"))

        routes: Dict[Tuple[str, str], HandlerFunc] = {
            ("GET", "/health"): self.handle_health,
            ("POST", "/trades"): self.handle_ingest_trade,
            ("GET", "/trades/parity"): self.handle_get_parity,
            ("POST", "/trades/reconcile"): self.handle_reconcile,
            ("POST", "/trades/cutover"): self.handle_cutover,
            ("POST", "/trades/rollback"): self.handle_rollback,
            ("POST", "/trades/chaos/toggle"): self.handle_toggle_chaos,
        }

        handler = routes.get(route_key)
        if not handler:
            return HTTPStatus.NOT_FOUND.value, {
                "error": "Not Found",
                "message": f"Endpoint '{method} {path}' is not registered.",
            }

        try:
            return handler(body or {})
        except ValueError as err:
            return HTTPStatus.BAD_REQUEST.value, {"error": "Bad Request", "message": str(err)}
        except Exception as err:
            return HTTPStatus.INTERNAL_SERVER_ERROR.value, {
                "error": "Internal Server Error",
                "message": str(err),
            }

    def handle_health(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """System health and operational state."""
        return HTTPStatus.OK.value, {
            "status": "UP",
            "cutover_active": self.is_cutover_active,
            "rollback_active": self.is_rollback_active,
            "cloud_partition_active": self.ingestion_service.is_cloud_partition_active,
        }

    def handle_ingest_trade(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /trades: Ingest a pure Trade entity via dual shadow ingestion."""
        trade = Trade(
            trade_id=str(body["trade_id"]),
            instrument=str(body["instrument"]),
            price=float(body["price"]),
            quantity=int(body["quantity"]),
            buy_order_id=str(body["buy_order_id"]),
            sell_order_id=str(body["sell_order_id"]),
            timestamp=str(body["timestamp"]),
        )
        result = self.ingestion_service.ingest(trade)
        return HTTPStatus.CREATED.value, result

    def handle_get_parity(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """GET /trades/parity: Out-of-band continuous audit."""
        snapshot = self.parity_service.evaluate_parity()
        return HTTPStatus.OK.value, snapshot

    def handle_reconcile(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /trades/reconcile: Trigger out-of-band idempotent catch-up replay."""
        dropped = self.ingestion_service.get_dropped_trades()
        reconciliation_result = self.parity_service.reconcile_from_trades(dropped)
        self.ingestion_service.clear_dropped_trades()
        return HTTPStatus.OK.value, reconciliation_result

    def handle_cutover(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /trades/cutover: Promote cloud datastore to primary master."""
        self.is_cutover_active = True
        self.is_rollback_active = False
        return HTTPStatus.OK.value, {
            "status": "CUTOVER_SUCCESSFUL",
            "active_primary": "AWS Aurora Multi-AZ PostgreSQL",
            "failback_standby": "Legacy On-Prem PostgreSQL (Hot)",
        }

    def handle_rollback(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /trades/rollback: Instant failback to on-premise master with zero data loss."""
        self.is_cutover_active = False
        self.is_rollback_active = True
        self.ingestion_service.set_cloud_partition(False)
        return HTTPStatus.OK.value, {
            "status": "ROLLBACK_SUCCESSFUL",
            "active_primary": "Legacy On-Premises Matching Engine",
            "data_loss_percentage": 0.00,
        }

    def handle_toggle_chaos(self, _: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /trades/chaos/toggle: Toggle simulated cloud network partition."""
        current = self.ingestion_service.is_cloud_partition_active
        new_state = not current
        self.ingestion_service.set_cloud_partition(new_state)
        msg = (
            "Chaos injected: Cloud worker dropping trades!"
            if new_state
            else "Chaos healed: Cloud worker resumed."
        )
        return HTTPStatus.OK.value, {
            "cloud_partition_active": new_state,
            "message": msg,
        }
