"""Unit tests for the RequestStateMachine validating all legal and illegal transitions."""

import pytest
from backend.models.enums import RequestStatus
from backend.services.state_machine import InvalidStateTransitionError, RequestStateMachine


def test_legal_happy_path_transitions():
    """Validates the standard legal happy-path transitions."""
    status = RequestStatus.DRAFT

    status = RequestStateMachine.transition(status, RequestStatus.PENDING_APPROVAL)
    assert status == RequestStatus.PENDING_APPROVAL

    status = RequestStateMachine.transition(status, RequestStatus.APPROVED)
    assert status == RequestStatus.APPROVED

    status = RequestStateMachine.transition(status, RequestStatus.QUEUED)
    assert status == RequestStatus.QUEUED

    status = RequestStateMachine.transition(status, RequestStatus.RUNNING)
    assert status == RequestStatus.RUNNING

    status = RequestStateMachine.transition(status, RequestStatus.VERIFYING)
    assert status == RequestStatus.VERIFYING

    status = RequestStateMachine.transition(status, RequestStatus.COMPLETED)
    assert status == RequestStatus.COMPLETED


def test_legal_rejection_and_cancellation():
    """Validates valid rejections and pre-run cancellations."""
    # Rejection from pending approval
    assert RequestStateMachine.can_transition(RequestStatus.PENDING_APPROVAL, RequestStatus.REJECTED)

    # Cancellation from draft
    assert RequestStateMachine.can_transition(RequestStatus.DRAFT, RequestStatus.CANCELLED)

    # Cancellation from pending approval
    assert RequestStateMachine.can_transition(RequestStatus.PENDING_APPROVAL, RequestStatus.CANCELLED)

    # Cancellation from approved
    assert RequestStateMachine.can_transition(RequestStatus.APPROVED, RequestStatus.CANCELLED)

    # Cancellation from queued
    assert RequestStateMachine.can_transition(RequestStatus.QUEUED, RequestStatus.CANCELLED)


def test_illegal_transitions_raise_error():
    """Validates that illegal transitions raise InvalidStateTransitionError."""
    # Cannot jump from DRAFT to COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        RequestStateMachine.transition(RequestStatus.DRAFT, RequestStatus.COMPLETED)

    # Cannot jump from PENDING_APPROVAL to RUNNING (bypassing approval!)
    with pytest.raises(InvalidStateTransitionError):
        RequestStateMachine.transition(RequestStatus.PENDING_APPROVAL, RequestStatus.RUNNING)

    # Cannot cancel after RUNNING
    assert not RequestStateMachine.can_transition(RequestStatus.RUNNING, RequestStatus.CANCELLED)
    with pytest.raises(InvalidStateTransitionError):
        RequestStateMachine.transition(RequestStatus.RUNNING, RequestStatus.CANCELLED)

    # Terminal states cannot transition anywhere
    assert not RequestStateMachine.can_transition(RequestStatus.COMPLETED, RequestStatus.PENDING_APPROVAL)
    with pytest.raises(InvalidStateTransitionError):
        RequestStateMachine.transition(RequestStatus.COMPLETED, RequestStatus.DRAFT)
