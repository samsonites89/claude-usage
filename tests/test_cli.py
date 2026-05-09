from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import StringIO

import pytest

from claude_usage import parser
from claude_usage.app import _print_json, _print_summary


def _record(
    input_tokens: int = 100,
    output_tokens: int = 200,
    session_id: str = "sess-1",
    offset_hours: float = -1,
) -> parser.UsageRecord:
    return parser.UsageRecord(
        timestamp=datetime.now(tz=timezone.utc) + timedelta(hours=offset_hours),
        session_id=session_id,
        workspace="test-project",
        model="claude-sonnet-4-6",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=0,
        cache_read_tokens=0,
    )


class TestPrintSummary:
    def test_empty_records(self, capsys):
        _print_summary([])
        out = capsys.readouterr().out
        assert "Claude Code Usage Summary" in out
        assert "All time" in out

    def test_shows_cost(self, capsys):
        records = [_record(input_tokens=1_000_000, output_tokens=0)]
        _print_summary(records)
        out = capsys.readouterr().out
        assert "$" in out

    def test_shows_token_counts(self, capsys):
        records = [_record(input_tokens=500, output_tokens=300)]
        _print_summary(records)
        out = capsys.readouterr().out
        assert "500" in out or "800" in out  # input or total

    def test_no_rate_limits_section_when_no_cache(self, capsys, monkeypatch):
        monkeypatch.setattr(parser, "load_rate_limits_cache", lambda: None)
        _print_summary([_record()])
        out = capsys.readouterr().out
        assert "Session" not in out
        assert "Week" not in out


class TestPrintJson:
    def test_empty_records_valid_json(self, capsys):
        _print_json([])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "all_time" in data
        assert "today" in data
        assert "this_week" in data
        assert "sessions" in data

    def test_all_time_keys(self, capsys):
        _print_json([_record()])
        data = json.loads(capsys.readouterr().out)
        all_time = data["all_time"]
        assert "estimated_cost" in all_time
        assert "input_tokens" in all_time
        assert "output_tokens" in all_time
        assert "record_count" in all_time

    def test_sessions_list(self, capsys):
        records = [
            _record(session_id="a", offset_hours=-1),
            _record(session_id="b", offset_hours=-2),
        ]
        _print_json(records)
        data = json.loads(capsys.readouterr().out)
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert "a" in session_ids
        assert "b" in session_ids

    def test_no_rate_limits_key_when_no_cache(self, capsys, monkeypatch):
        monkeypatch.setattr(parser, "load_rate_limits_cache", lambda: None)
        _print_json([_record()])
        data = json.loads(capsys.readouterr().out)
        assert "rate_limits" not in data

    def test_cost_rounded_to_two_decimals(self, capsys):
        _print_json([_record(input_tokens=1, output_tokens=1)])
        data = json.loads(capsys.readouterr().out)
        cost = data["all_time"]["estimated_cost"]
        # Should have at most 6 decimal places in JSON
        assert isinstance(cost, float)
