"""Unit tests for model serialization overrides."""

import datetime

from rx_shout.models import Entry


def test_entry_dict_truncates_ts_microseconds():
    """Entry.dict() serializes ts as an isoformat string without microseconds."""
    ts = datetime.datetime(2026, 7, 2, 12, 34, 56, 789012, tzinfo=datetime.UTC)
    entry = Entry(ts=ts, author_id=1, text="hello")
    d = entry.dict()
    assert d["ts"] == "2026-07-02T12:34:56+00:00"
    assert d["text"] == "hello"
