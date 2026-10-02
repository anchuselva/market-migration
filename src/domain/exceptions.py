"""Domain-specific exceptions for financial trading and migration system."""


class DomainException(Exception):
    """Base class for all domain-level business rule violations."""
    pass


class ValidationError(DomainException):
    """Raised when an entity fails validation invariant rules."""
    pass


class InvalidPriceError(ValidationError):
    """Raised when trade or order price is non-positive or invalid."""
    pass


class InvalidQuantityError(ValidationError):
    """Raised when trade or order quantity is non-positive or invalid."""
    pass


class InvalidTradeIdError(ValidationError):
    """Raised when a trade ID is missing or malformed."""
    pass


class ParityDriftError(DomainException):
    """Raised when out-of-band parity auditor detects unrecoverable state drift."""
    pass


class ReconciliationError(DomainException):
    """Raised when automatic replay fails to achieve 100% store parity."""
    pass
