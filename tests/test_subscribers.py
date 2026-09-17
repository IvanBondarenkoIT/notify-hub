"""Pure-function tests for subscription matching (no DB / no Telegram)."""

from notify_hub.subscribers import (
    DEFAULT_CALENDAR_PREFIX,
    event_matches_prefix,
    filter_matching_subscriptions,
    merge_chat_targets,
    normalize_prefix,
)


def test_normalize_prefix_calendar():
    assert normalize_prefix("calendar") == "calendar."
    assert normalize_prefix("calendar.") == "calendar."
    assert normalize_prefix(DEFAULT_CALENDAR_PREFIX) == "calendar."


def test_event_matches_prefix():
    assert event_matches_prefix("calendar.event.v1", "calendar.")
    assert event_matches_prefix("calendar.event.v1", "calendar")
    assert event_matches_prefix("calendar.event.v1", "calendar.event.v1")
    assert not event_matches_prefix("stock.alert.v1", "calendar.")
    assert not event_matches_prefix("", "calendar.")
    assert event_matches_prefix("calendar.reminder", "calendar*")


def test_filter_matching_subscriptions():
    subs = [
        (1, "calendar.", "public"),
        (2, "stock.", "public"),
        (3, "calendar.event.v1", "public"),
    ]
    matched = filter_matching_subscriptions("calendar.event.v1", subs)
    chat_ids = {m[0] for m in matched}
    assert chat_ids == {1, 3}


def test_merge_chat_targets_dedup_order():
    assert merge_chat_targets([10, 20], [20, 30, 10]) == [10, 20, 30]
    assert merge_chat_targets([], []) == []
