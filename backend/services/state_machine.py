"""State machine enforcing legal transitions for wipe requests and lifecycle operations."""

from typing import Dict, Set
from backend.models.enums import RequestStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""
    def __init__(self, current_status: RequestStatus, target_status: RequestStatus):
        super().__init__(
            f"Illegal state transition from '{current_status.value}' to '{target_status.value}'"
        )
        self.current_status = current_status
        self.target_status = target_status


class RequestStateMachine:
    """Enforces NIST-aligned wipe request lifecycle state transitions."""

    LEGAL_TRANSITIONS: Dict[RequestStatus, Set[RequestStatus]] = {
        RequestStatus.DRAFT: {
            RequestStatus.PENDING_APPROVAL,
            RequestStatus.CANCELLED,
        },
        RequestStatus.PENDING_APPROVAL: {
            RequestStatus.APPROVED,
            RequestStatus.REJECTED,
            RequestStatus.EXPIRED,
            RequestStatus.CANCELLED,
        },
        RequestStatus.APPROVED: {
            RequestStatus.QUEUED,
            RequestStatus.EXPIRED,
            RequestStatus.CANCELLED,
        },
        RequestStatus.QUEUED: {
            RequestStatus.RUNNING,
            RequestStatus.CANCELLED,
            RequestStatus.FAILED,
        },
        RequestStatus.RUNNING: {
            RequestStatus.VERIFYING,
            RequestStatus.FAILED,
        },
        RequestStatus.VERIFYING: {
            RequestStatus.COMPLETED,
            RequestStatus.FAILED,
        },
        # Terminal states
        RequestStatus.COMPLETED: set(),
        RequestStatus.REJECTED: set(),
        RequestStatus.EXPIRED: set(),
        RequestStatus.FAILED: set(),
        RequestStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, current: RequestStatus, target: RequestStatus) -> bool:
        """Checks if a transition from current to target status is valid."""
        if current == target:
            return True
        allowed = cls.LEGAL_TRANSITIONS.get(current, set())
        return target in allowed

    @classmethod
    def transition(cls, current: RequestStatus, target: RequestStatus) -> RequestStatus:
        """Validates and returns the target status, or raises InvalidStateTransitionError."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(current, target)
        return target
