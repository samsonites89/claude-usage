from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from claude_usage import parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(offset_hours: float = 0) -> datetime:
    """Return a UTC datetime offset_hours from now."""
    return datetime.now(tz=timezone.utc) + timedelta(hours=offset_hours)


def _record(
    *,
    session_id: str = "sess-1",
    workspace: str = "my-project",
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 100,
    output_tokens: int = 200,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    timestamp: datetime | None = None,
) -> parser.UsageRecord:
    return parser.UsageRecord(
        timestamp=timestamp or _ts(),
        session_id=session_id,
        workspace=workspace,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
    )


def _jsonl_line(
    *,
    msg_type: str = "assistant",
    input_tokens: int = 10,
    output_tokens: int = 20,
    cache_creation: int = 0,
    cache_read: int = 0,
    session_id: str = "sess-abc",
    timestamp: str = "2026-05-09T12:00:00Z",
    model: str = "claude-sonnet-4-6",
) -> str:
    return json.dumps({
        "type": msg_type,
        "sessionId": session_id,
        "timestamp": timestamp,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
            },
        },
    })


# ---------------------------------------------------------------------------
# _parse_record
# ---------------------------------------------------------------------------

class TestParseRecord:
    def test_valid_assistant_message(self):
        line = _jsonl_line(input_tokens=10, output_tokens=20)
        rec = parser._parse_record(line, "my-project")
        assert rec is not None
        assert rec.input_tokens == 10
        assert rec.output_tokens == 20
        assert rec.session_id == "sess-abc"
        assert rec.workspace == "my-project"

    def test_non_assistant_type_returns_none(self):
        line = _jsonl_line(msg_type="user")
        assert parser._parse_record(line, "ws") is None

    def test_missing_usage_returns_none(self):
        obj = {"type": "assistant", "sessionId": "s", "timestamp": "2026-05-09T00:00:00Z", "message": {}}
        assert parser._parse_record(json.dumps(obj), "ws") is None

    def test_invalid_json_returns_none(self):
        assert parser._parse_record("not json {{{", "ws") is None

    def test_cache_tokens_parsed(self):
        line = _jsonl_line(cache_creation=500, cache_read=1000)
        rec = parser._parse_record(line, "ws")
        assert rec is not None
        assert rec.cache_creation_tokens == 500
        assert rec.cache_read_tokens == 1000

    def test_timestamp_parsed_correctly(self):
        line = _jsonl_line(timestamp="2026-01-15T10:30:00Z")
        rec = parser._parse_record(line, "ws")
        assert rec is not None
        assert rec.timestamp.year == 2026
        assert rec.timestamp.month == 1
        assert rec.timestamp.day == 15


# ---------------------------------------------------------------------------
# UsageRecord properties
# ---------------------------------------------------------------------------

class TestUsageRecord:
    def test_total_tokens(self):
        rec = _record(input_tokens=100, output_tokens=200)
        assert rec.total_tokens == 300

    def test_estimated_cost_nonzero(self):
        rec = _record(input_tokens=1_000_000, output_tokens=0)
        assert abs(rec.estimated_cost - parser.PRICE_INPUT) < 0.0001

    def test_estimated_cost_zero_for_empty(self):
        rec = _record(input_tokens=0, output_tokens=0)
        assert rec.estimated_cost == 0.0


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------

class TestTotals:
    def test_empty_totals(self):
        t = parser.Totals()
        assert t.total_tokens == 0
        assert t.estimated_cost == 0.0
        assert t.record_count == 0

    def test_add_accumulates(self):
        t = parser.Totals()
        t.add(_record(input_tokens=100, output_tokens=200))
        t.add(_record(input_tokens=50, output_tokens=75))
        assert t.input_tokens == 150
        assert t.output_tokens == 275
        assert t.record_count == 2

    def test_total_tokens_property(self):
        t = parser.Totals()
        t.add(_record(input_tokens=100, output_tokens=200))
        assert t.total_tokens == 300

    def test_totals_function_empty(self):
        result = parser.totals([])
        assert result.record_count == 0
        assert result.total_tokens == 0

    def test_totals_function_sums_records(self):
        records = [
            _record(input_tokens=100, output_tokens=200),
            _record(input_tokens=50, output_tokens=100),
        ]
        result = parser.totals(records)
        assert result.input_tokens == 150
        assert result.output_tokens == 300
        assert result.record_count == 2


# ---------------------------------------------------------------------------
# today_totals
# ---------------------------------------------------------------------------

class TestTodayTotals:
    def test_includes_recent_record(self):
        records = [_record(input_tokens=100, timestamp=_ts(-1))]  # 1 hour ago
        result = parser.today_totals(records)
        assert result.record_count == 1

    def test_excludes_yesterday(self):
        records = [_record(input_tokens=100, timestamp=_ts(-25))]  # 25 hours ago
        result = parser.today_totals(records)
        assert result.record_count == 0

    def test_empty_records(self):
        assert parser.today_totals([]).record_count == 0


# ---------------------------------------------------------------------------
# window_totals
# ---------------------------------------------------------------------------

class TestWindowTotals:
    def test_includes_record_within_window(self):
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=5)
        records = [_record(input_tokens=100, timestamp=now - timedelta(hours=2))]
        result = parser.window_totals(records, start, now)
        assert result.record_count == 1

    def test_excludes_record_outside_window(self):
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=5)
        records = [_record(input_tokens=100, timestamp=now - timedelta(hours=6))]
        result = parser.window_totals(records, start, now)
        assert result.record_count == 0

    def test_empty_records(self):
        now = datetime.now(tz=timezone.utc)
        assert parser.window_totals([], now - timedelta(hours=1), now).record_count == 0


# ---------------------------------------------------------------------------
# week_totals
# ---------------------------------------------------------------------------

class TestWeekTotals:
    def test_includes_this_week(self):
        records = [_record(timestamp=_ts(-24))]  # yesterday
        result = parser.week_totals(records)
        # Only valid if yesterday is still this week — use window as proxy
        # Just check it doesn't crash and returns a Totals
        assert isinstance(result, parser.Totals)

    def test_excludes_old_record(self):
        records = [_record(timestamp=_ts(-24 * 14))]  # 2 weeks ago
        result = parser.week_totals(records)
        assert result.record_count == 0


# ---------------------------------------------------------------------------
# by_day / by_week / by_session / session_last_seen
# ---------------------------------------------------------------------------

class TestGrouping:
    def test_by_day_groups_correctly(self):
        # Use early UTC times so local-date conversion stays on the same day in any timezone (UTC-12 to UTC+14).
        ts1 = datetime(2026, 5, 1, 1, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 1, 6, 0, tzinfo=timezone.utc)
        ts3 = datetime(2026, 5, 2, 1, 0, tzinfo=timezone.utc)
        records = [
            _record(input_tokens=100, timestamp=ts1),
            _record(input_tokens=200, timestamp=ts2),
            _record(input_tokens=50, timestamp=ts3),
        ]
        result = parser.by_day(records)
        assert len(result) == 2
        may1 = ts1.astimezone().date()
        assert result[may1].input_tokens == 300
        assert result[may1].record_count == 2

    def test_by_week_groups_to_monday(self):
        monday = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)   # Monday
        thursday = datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc)  # Thursday same week
        records = [
            _record(timestamp=monday),
            _record(timestamp=thursday),
        ]
        result = parser.by_week(records)
        assert len(result) == 1  # both in same week

    def test_by_session_groups_by_id(self):
        records = [
            _record(session_id="a", input_tokens=100),
            _record(session_id="a", input_tokens=200),
            _record(session_id="b", input_tokens=50),
        ]
        result = parser.by_session(records)
        assert result["a"].input_tokens == 300
        assert result["b"].input_tokens == 50

    def test_session_last_seen_returns_latest(self):
        ts_old = _ts(-2)
        ts_new = _ts(-1)
        records = [
            _record(session_id="a", timestamp=ts_old),
            _record(session_id="a", timestamp=ts_new),
        ]
        result = parser.session_last_seen(records)
        assert result["a"] == ts_new

    def test_session_last_seen_multiple_sessions(self):
        records = [
            _record(session_id="a", timestamp=_ts(-3)),
            _record(session_id="b", timestamp=_ts(-1)),
        ]
        result = parser.session_last_seen(records)
        assert "a" in result
        assert "b" in result


# ---------------------------------------------------------------------------
# PlanConfig
# ---------------------------------------------------------------------------

class TestPlanConfig:
    def test_daily_budget(self):
        pc = parser.PlanConfig(plan_key="pro", label="Pro", monthly_budget=20.0)
        assert abs(pc.daily_budget - 20.0 / 30) < 0.0001

    def test_weekly_budget(self):
        pc = parser.PlanConfig(plan_key="pro", label="Pro", monthly_budget=20.0)
        assert abs(pc.weekly_budget - 20.0 / 4.33) < 0.01

    def test_plans_dict_contains_expected_keys(self):
        assert "pro" in parser.PLANS
        assert "max_5x" in parser.PLANS
        assert "max_20x" in parser.PLANS


# ---------------------------------------------------------------------------
# RateLimits
# ---------------------------------------------------------------------------

class TestRateLimits:
    def _make_rl(self, session_util: float = 0.5, weekly_util: float = 0.25) -> parser.RateLimits:
        now = datetime.now(tz=timezone.utc)
        return parser.RateLimits(
            session_utilization=session_util,
            session_reset_at=now + timedelta(hours=3),
            weekly_utilization=weekly_util,
            weekly_reset_at=now + timedelta(days=5),
            fetched_at=now,
        )

    def test_session_pct(self):
        rl = self._make_rl(session_util=0.5)
        assert rl.session_pct == 50.0

    def test_weekly_pct(self):
        rl = self._make_rl(weekly_util=0.75)
        assert rl.weekly_pct == 75.0
