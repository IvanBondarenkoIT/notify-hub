"""Ack status transition pure tests (stub escalate ticker)."""

from notify_hub.ack import (
    ACK_ACKNOWLEDGED,
    ACK_ESCALATED,
    ACK_EXPIRED,
    ACK_PENDING,
    can_transition,
    next_ack_status_on_timeout,
)


def test_can_transition_pending():
    assert can_transition(ACK_PENDING, ACK_ACKNOWLEDGED)
    assert can_transition(ACK_PENDING, ACK_ESCALATED)
    assert can_transition(ACK_PENDING, ACK_EXPIRED)
    assert can_transition(ACK_PENDING, ACK_PENDING)
    assert not can_transition(ACK_ACKNOWLEDGED, ACK_PENDING)
    assert not can_transition(ACK_ACKNOWLEDGED, ACK_ESCALATED)


def test_next_ack_status_on_timeout():
    assert (
        next_ack_status_on_timeout(
            ACK_PENDING, timed_out=True, escalate_configured=True
        )
        == ACK_ESCALATED
    )
    assert (
        next_ack_status_on_timeout(
            ACK_PENDING, timed_out=True, escalate_configured=False
        )
        == ACK_EXPIRED
    )
    assert (
        next_ack_status_on_timeout(
            ACK_PENDING, timed_out=False, escalate_configured=True
        )
        is None
    )
    assert (
        next_ack_status_on_timeout(
            ACK_ACKNOWLEDGED, timed_out=True, escalate_configured=True
        )
        is None
    )
